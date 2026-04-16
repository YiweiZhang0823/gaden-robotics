#!/usr/bin/env python3
"""
订阅末端位姿目标 /franka_ee_goal (geometry_msgs/PoseStamped)，在 base 系下做数值 IK，
向 /franka_joint_target 发布 fp3_joint1..7，与 franka_joint_interactive 配合使用。

使用前请保持: joint_state_mode:=interactive

示例（目标在 base 系，单位米）:
  ros2 topic pub --once /franka_ee_goal geometry_msgs/msg/PoseStamped "
  header:
    frame_id: base
  pose:
    position: {x: 0.4, y: 0.0, z: 0.45}
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  "

  # 多行 YAML 易解析失败时，用单行（推荐）：
  # ros2 topic pub -1 /franka_ee_goal geometry_msgs/msg/PoseStamped \\
  #   "{header: {frame_id: base}, pose: {position: {x: 0.4, y: 0.0, z: 0.45}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}"

frame_id 为 map 时会用 TF 转到 base（需已有 map->base）。

若 RViz 末端「怎么发都差不多」：看终端是否出现「收到末端目标」里 xyz 是否真的在变；
若不变，多为 ros2 topic pub 多行 YAML 未正确解析，请改用单行 JSON（见下方示例）。
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import PyKDL as kdl
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Pose, PoseStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from tf2_geometry_msgs.tf2_geometry_msgs import do_transform_pose


def _load_chain() -> kdl.Chain:
    kinematics_path = Path(get_package_share_directory("franka_description")) / "robots" / "fp3" / "kinematics.yaml"
    with kinematics_path.open() as f:
        kin = yaml.safe_load(f)

    def frame_from_k(data: dict) -> kdl.Frame:
        k = data["kinematic"]
        return kdl.Frame(
            kdl.Rotation.RPY(k["roll"], k["pitch"], k["yaw"]),
            kdl.Vector(k["x"], k["y"], k["z"]),
        )

    chain = kdl.Chain()
    for i in range(1, 8):
        chain.addSegment(
            kdl.Segment(kdl.Joint(kdl.Joint.RotZ), frame_from_k(kin[f"joint{i}"]))
        )
    chain.addSegment(
        kdl.Segment(kdl.Joint(kdl.Joint.Fixed), frame_from_k(kin["joint8"]))
    )
    chain.addSegment(
        kdl.Segment(
            kdl.Joint(kdl.Joint.Fixed),
            kdl.Frame(kdl.Vector(0.0, 0.0, 0.1034)),
        )
    )
    return chain


def _normalize_pose_orientation(msg: Pose) -> None:
    """无效或零四元数会使 KDL Quaternion 数值不稳定，表现为 IK 结果异常或几乎不变。"""
    q = msg.orientation
    n = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w)
    if not math.isfinite(n) or n < 1e-9:
        msg.orientation.x = 0.0
        msg.orientation.y = 0.0
        msg.orientation.z = 0.0
        msg.orientation.w = 1.0
        return
    inv = 1.0 / n
    msg.orientation.x *= inv
    msg.orientation.y *= inv
    msg.orientation.z *= inv
    msg.orientation.w *= inv


def _pose_to_kdl_frame(msg) -> kdl.Frame:
    """geometry_msgs 四元数 (x,y,z,w) 与 PyKDL Rotation.Quaternion 顺序一致；勿对调 w。"""
    p = msg.position
    q = msg.orientation
    return kdl.Frame(
        kdl.Rotation.Quaternion(q.x, q.y, q.z, q.w),
        kdl.Vector(p.x, p.y, p.z),
    )


def _quat_slerp_xyzw(
    q0: tuple[float, float, float, float],
    q1: tuple[float, float, float, float],
    t: float,
) -> tuple[float, float, float, float]:
    """PyKDL GetQuaternion() 为 (x,y,z,w)，球面插值，避免 RPY 分量线性插值在万向节附近乱拧。"""
    x0, y0, z0, w0 = q0
    x1, y1, z1, w1 = q1
    tt = max(0.0, min(1.0, float(t)))
    dot = x0 * x1 + y0 * y1 + z0 * z1 + w0 * w1
    if dot < 0.0:
        x1, y1, z1, w1 = -x1, -y1, -z1, -w1
        dot = -dot
    if dot > 0.9995:
        x = (1.0 - tt) * x0 + tt * x1
        y = (1.0 - tt) * y0 + tt * y1
        z = (1.0 - tt) * z0 + tt * z1
        w = (1.0 - tt) * w0 + tt * w1
    else:
        theta = math.acos(max(min(dot, 1.0), -1.0))
        st = math.sin(theta)
        s0 = math.sin((1.0 - tt) * theta) / st
        s1 = math.sin(tt * theta) / st
        x = s0 * x0 + s1 * x1
        y = s0 * y0 + s1 * y1
        z = s0 * z0 + s1 * z1
        w = s0 * w0 + s1 * w1
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        return x0, y0, z0, w0
    inv = 1.0 / n
    return x * inv, y * inv, z * inv, w * inv


# 与 franka_joint_interactive 初值一致。PyKDL FK 下 TCP 约在 base 前方 x≈0.09m、侧向 y≈0，比大负 j2/j4 更「竖在基座前」。
_FP3_READY_SEED_RAD = (0.0, -0.3, 0.0, -1.4, 0.0, 1.7, 0.0)
# PyKDL LMA 不遵守 URDF 限位，解可能 j6<0.44 或 j4 越界 → RViz 折断；发布前饱和到合法区间（与之前「顶在极限」不同：那是解本身已坏）。
_FP3_LIMITS_LO = (-2.9007, -1.8361, -2.9007, -3.0770, -2.8763, 0.4398, -3.0508)
_FP3_LIMITS_HI = (2.9007, 1.8361, 2.9007, -0.1169, 2.8763, 4.6216, 3.0508)


def _clamp_fp3_jnt(q: kdl.JntArray) -> None:
    for i in range(7):
        v = float(q[i])
        lo, hi = _FP3_LIMITS_LO[i], _FP3_LIMITS_HI[i]
        q[i] = max(lo, min(hi, v))


def _kdl_ready_seed() -> kdl.JntArray:
    j = kdl.JntArray(7)
    for i in range(7):
        j[i] = _FP3_READY_SEED_RAD[i]
    return j


def _low_reach_bias_seed() -> kdl.JntArray:
    """肩肘更前倾，用作够低目标时的额外 LMA 种子（与就绪角同限位内）。"""
    j = kdl.JntArray(7)
    for i, v in enumerate((0.0, -0.88, 0.12, -2.45, 0.0, 2.82, 0.0)):
        j[i] = v
    _clamp_fp3_jnt(j)
    return j


def _jnt_copy(src: kdl.JntArray) -> kdl.JntArray:
    out = kdl.JntArray(7)
    for i in range(7):
        out[i] = float(src[i])
    return out


def _clamped_copy(q: kdl.JntArray) -> kdl.JntArray:
    """与发布到 /franka_joint_target 一致：先钳位再评价，否则选解会挑到「未钳位时 j2 好看、钳位后 j4/j6 贴死」的假优解。"""
    qc = _jnt_copy(q)
    _clamp_fp3_jnt(qc)
    return qc


def _joint_limit_compression_penalty(q: kdl.JntArray, scale: float) -> float:
    """j4≈-3.077、j6≈0.44 贴下限时肘腕折到极限，RViz 里像整臂往地面塌；须重罚。"""
    j4 = float(q[3])
    j6 = float(q[5])
    c = 0.0
    if j4 <= -3.04:
        c += float(scale) * (2.0 + (-3.077 - j4) ** 2 * 25.0)
    elif j4 <= -2.78:
        c += float(scale) * 0.2
    if j6 <= 0.46:
        c += float(scale) * (2.0 + (0.46 - j6) ** 2 * 40.0)
    elif j6 <= 0.55:
        c += float(scale) * 0.15
    return c


def _joint_sq_dist(a: kdl.JntArray, b: kdl.JntArray) -> float:
    """关节空间 L2 距离平方，用于在冗余 IK 解中选与当前姿态最接近的一支。"""
    s = 0.0
    for i in range(7):
        d = float(a[i]) - float(b[i])
        s += d * d
    return s


def _joint_blend_cost(
    q: kdl.JntArray, cur: kdl.JntArray, ready: kdl.JntArray, w: float
) -> float:
    """w→1 偏重就绪（自然下探），w→0 偏重当前（连续）；中等 z 连续过渡，避免「中等高度却像猛往下够」。"""
    w = max(0.0, min(1.0, float(w)))
    return w * _joint_sq_dist(q, ready) + (1.0 - w) * _joint_sq_dist(q, cur)


def _goal_z_blend_w(z: float, z_hi: float, z_lo: float) -> float:
    """base 系 TCP z：z>=z_hi → w=0；z<=z_lo → w=1；中间线性。"""
    if z >= z_hi:
        return 0.0
    if z <= z_lo:
        return 1.0
    denom = z_hi - z_lo
    if denom <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (z_hi - z) / denom))


def _mid_forward_probe_seed() -> kdl.JntArray:
    """前方中等高度探视：肩勿过负、肘略展，避免初值像「往基座脚下缩」。"""
    j = kdl.JntArray(7)
    for i, v in enumerate((0.0, -0.40, -0.05, -1.65, 0.0, 2.05, 0.0)):
        j[i] = v
    _clamp_fp3_jnt(j)
    return j


def _mid_forward_collapse_penalty(
    q: kdl.JntArray, gx: float, gz: float, scale: float
) -> float:
    """base 系前方中等高度目标：冗余解里肩角 j2 过负时像「瘫向脚下」；对 j2 过负加罚，保留可达性。"""
    if gx < 0.30 or gz < 0.34 or gz > 0.64:
        return 0.0
    j2 = float(q[1])
    # 就绪约 -0.3；缩团/下折常见 j2 < -0.85
    thr = -0.76
    if j2 < thr:
        return float(scale) * (j2 - thr) ** 2
    return 0.0


def _is_forward_mid_probe(gx: float, gz: float) -> bool:
    """base 系前伸、中等高度（典型探视区），易出「往脚下缩」冗余解。"""
    return gx >= 0.28 and 0.32 <= gz <= 0.64


def _upright_forward_seed() -> kdl.JntArray:
    """肩角接近就绪、略抬：作前伸中等目标时的优先 LMA 初值。"""
    j = kdl.JntArray(7)
    for i, v in enumerate((0.0, -0.26, 0.0, -1.38, 0.0, 1.72, 0.0)):
        j[i] = v
    _clamp_fp3_jnt(j)
    return j


def _extended_reach_seed_templates() -> list[kdl.JntArray]:
    """
    与 fp3 joint 限位一致、偏向「肩抬、肘展开、往前方探」的关节角（rad），
    用作 LMA 多种子之一，减轻「全缩在身体前再往下绕」的冗余解。
    """
    # joint4 必须 < 0（见 joint_limits.yaml）；joint6 必须 > ~0.44
    raw = [
        [0.0, -0.55, 0.0, -2.15, 0.0, 2.65, 0.0],
        [0.0, -0.75, 0.15, -2.35, 0.0, 2.85, 0.2],
        [0.15, -0.5, -0.2, -2.05, 0.0, 2.55, -0.15],
    ]
    out: list[kdl.JntArray] = []
    for row in raw:
        j = kdl.JntArray(7)
        for i in range(7):
            j[i] = row[i]
        out.append(j)
    return out


def _interp_frame(F0: kdl.Frame, F1: kdl.Frame, alpha: float) -> kdl.Frame:
    """位置线性插值；姿态用四元数 SLERP（与 KDL 一致），勿用 RPY 分量线性插值（会与 KDL RPY 定义不一致且过万向节时乱拧）。"""
    a = max(0.0, min(1.0, float(alpha)))
    p0, p1 = F0.p, F1.p
    px = (1.0 - a) * float(p0[0]) + a * float(p1[0])
    py = (1.0 - a) * float(p0[1]) + a * float(p1[1])
    pz = (1.0 - a) * float(p0[2]) + a * float(p1[2])
    q0 = F0.M.GetQuaternion()
    q1 = F1.M.GetQuaternion()
    qx, qy, qz, qw = _quat_slerp_xyzw(q0, q1, a)
    return kdl.Frame(
        kdl.Rotation.Quaternion(qx, qy, qz, qw),
        kdl.Vector(px, py, pz),
    )


def _frame_near(a: kdl.Frame, b: kdl.Frame | None, pos_eps: float, ang_eps: float) -> bool:
    """与上一目标几乎相同则不再算 IK，避免 LMA 在相近解之间来回跳导致 RViz 抽动。"""
    if b is None:
        return False
    for i in range(3):
        if abs(float(a.p[i]) - float(b.p[i])) > pos_eps:
            return False
    r1 = a.M.GetRPY()
    r2 = b.M.GetRPY()
    for i in range(3):
        if abs(float(r1[i]) - float(r2[i])) > ang_eps:
            return False
    return True


class FrankaFp3IkGoal(Node):
    JOINT_NAMES = [f"fp3_joint{i}" for i in range(1, 8)]

    def __init__(self):
        super().__init__("franka_fp3_ik_goal")
        self._chain = _load_chain()
        self._fk = kdl.ChainFkSolverPos_recursive(self._chain)
        # (chain, eps, maxiter, eps_joints)：默认 eps_joints=1e-15 易触发 E_INCREMENT_JOINTS_TOO_SMALL
        self._ik = kdl.ChainIkSolverPos_LMA(self._chain, 1e-4, 2000, 1e-9)
        self._q_seed = kdl.JntArray(7)
        for i in range(7):
            self._q_seed[i] = _FP3_READY_SEED_RAD[i]
        self._last_q_success = kdl.JntArray(7)
        self._have_last_q_success = False
        self._last_goal_frame: kdl.Frame | None = None
        # 默认 false：连续发不同坐标时易被误判「与上次几乎相同」或调试时看起来像「没动」。
        self.declare_parameter("skip_duplicate_cartesian", False)
        # 沿笛卡尔直线分段 IK；默认关（单次 IK + interactive 平滑已足够）。开 true 时易在中间段出现冗余解歧义、观感像乱折。
        self.declare_parameter("use_cartesian_path", False)
        self.declare_parameter("cartesian_path_steps", 24)
        # 当前关节角与已发布路径点足够接近时再发下一点（略大于典型插值步长，避免永远等不到）
        self.declare_parameter("waypoint_reach_tolerance_rad", 0.18)
        # 在数值 IK 中额外尝试「向前舒展」关节种子；默认开，且 min_x 须 <0.45 才会对 (0.45,0,0.5) 生效（旧默认 0.46 会导致永远「否」）。
        self.declare_parameter("prefer_extended_reach", True)
        # base 系：x/z 同时达到阈值才加舒展模板；z 过低不加，避免够低目标仍走「抬高肘」模板。
        self.declare_parameter("extended_reach_min_goal_z", 0.38)
        self.declare_parameter("extended_reach_min_goal_x", 0.38)
        # 随机扰动种子在「当前种子 IK 失败」时易先命中怪解（观感像突然往下栽）；默认 0，不再加随机种子。
        self.declare_parameter("ik_num_random_seeds", 0)
        # 冗余解代价 = w·‖q−就绪‖² + (1−w)·‖q−当前‖²；w 由目标 z 在 [ik_blend_z_lo, ik_blend_z_hi] 上连续变化。
        self.declare_parameter("ik_blend_z_hi", 0.66)
        self.declare_parameter("ik_blend_z_lo", 0.32)
        self.declare_parameter("ik_blend_mid_w_boost", 0.10)
        # 目标在「前伸 x、中等 z」带时额外增大 w，更偏向就绪姿态，减轻一上来就往脚下缩。
        self.declare_parameter("ik_forward_mid_w_extra", 0.14)
        # 前方中等高度时对 j2 过负的惩罚系数（越大越排斥「瘫缩」冗余解）。
        self.declare_parameter("ik_mid_collapse_penalty", 18.0)
        # 前伸中等：肩角 j2 拉向就绪附近（二次项）；勿再用「-w*j2」否则会把肩抬到指天。
        self.declare_parameter("ik_j2_pref", -0.32)
        self.declare_parameter("ik_j2_lift_weight", 14.0)
        # 前伸中等：先丢掉 j2 低于此值的候选；若全丢则改选 |j2-ik_j2_pref| 最小的一支。
        self.declare_parameter("ik_forward_j2_floor", -0.70)
        # 钳位后 j4/j6 贴下限（如日志 j4=-3.077,j6=0.44）的惩罚倍率。
        self.declare_parameter("ik_joint_limit_penalty", 110.0)
        # 钳位后 TCP 位置与目标的平方误差权重（避免钳位破坏末端位姿仍被选中）。
        self.declare_parameter("ik_fk_after_clamp_weight", 500.0)
        # 仅当 z 低于此值才加入「够低」偏置种子；勿与 ik_blend 混用旧阈值，否则 z≈0.5 会误加低姿种子导致猛往下够。
        self.declare_parameter("ik_low_extra_seed_z", 0.38)

        self._waypoint_queue: list[list[float]] | None = None
        self._waypoint_target: list[float] | None = None
        self._pending_final_goal_frame: kdl.Frame | None = None
        self._last_published_q: list[float] | None = None

        _target_qos = QoSProfile(
            depth=20,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._pub = self.create_publisher(
            JointState, "/franka_joint_target", _target_qos
        )
        self.create_subscription(
            PoseStamped,
            "/franka_ee_goal",
            self._on_goal,
            QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE),
        )
        # 与 franka_joint_interactive 发布端一致：用「当前真实关节角」作 LMA 种子，避免与平滑层脱节跳到另一解
        _js_qos = QoSProfile(
            depth=20,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.create_subscription(
            JointState,
            "/fp3_arm/joint_states",
            self._on_joint_states,
            _js_qos,
        )

        from tf2_ros import Buffer, TransformListener

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self.get_logger().info(
            "IK: /franka_ee_goal -> /franka_joint_target; seed from /fp3_arm/joint_states; "
            "use_cartesian_path:=true 时笛卡尔分段（默认 false，见参数）"
        )

    def _fk_frame(self, q: kdl.JntArray) -> kdl.Frame | None:
        f = kdl.Frame()
        err = self._fk.JntToCart(q, f)
        if err < 0:
            return None
        return f

    def _publish_joint_array(self, q_out: kdl.JntArray) -> None:
        _clamp_fp3_jnt(q_out)
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = list(self.JOINT_NAMES)
        js.position = [float(q_out[i]) for i in range(7)]
        self._pub.publish(js)

    def _use_extended_seeds_for_goal(self, goal: kdl.Frame) -> bool:
        """仅对「往远处、偏上」的目标启用舒展模板；够低/收近的目标用当前关节优先，避免一直抬头。"""
        if not bool(self.get_parameter("prefer_extended_reach").value):
            return False
        min_x = float(self.get_parameter("extended_reach_min_goal_x").value)
        min_z = float(self.get_parameter("extended_reach_min_goal_z").value)
        gx = float(goal.p[0])
        gz = float(goal.p[2])
        return gx >= min_x and gz >= min_z

    def _fk_position_err_sq(self, q: kdl.JntArray, goal: kdl.Frame) -> float:
        """钳位后 TCP 位置误差平方（米²）。"""
        fk = kdl.Frame()
        if self._fk.JntToCart(q, fk) < 0:
            return 1e9
        ex = float(fk.p[0]) - float(goal.p[0])
        ey = float(fk.p[1]) - float(goal.p[1])
        ez = float(fk.p[2]) - float(goal.p[2])
        return ex * ex + ey * ey + ez * ez

    def _solve_ik(self, goal: kdl.Frame) -> tuple[int, kdl.JntArray]:
        """多组种子 LMA；在成功解中用混合代价选冗余解，避免中等高度误用「够低」种子而像猛往下折。"""
        q_out = kdl.JntArray(7)
        want_ext = self._use_extended_seeds_for_goal(goal)
        ext = _extended_reach_seed_templates() if want_ext else []
        cur = _jnt_copy(self._q_seed)
        # 勿用全零作种子：fp3 的 joint4/joint6 不能为 0，零种子易让 LMA 落到异常分支，观感像栽倒。
        ready_fallback = _kdl_ready_seed()
        gx = float(goal.p[0])
        gz = float(goal.p[2])
        z_hi = float(self.get_parameter("ik_blend_z_hi").value)
        z_lo = float(self.get_parameter("ik_blend_z_lo").value)
        low_seed_z = float(self.get_parameter("ik_low_extra_seed_z").value)

        w = _goal_z_blend_w(gz, z_hi, z_lo)
        if z_lo <= gz <= z_hi:
            w = min(1.0, w + float(self.get_parameter("ik_blend_mid_w_boost").value))
        if gx >= 0.34 and 0.36 <= gz <= 0.60:
            w = min(1.0, w + float(self.get_parameter("ik_forward_mid_w_extra").value))

        pen_scale = float(self.get_parameter("ik_mid_collapse_penalty").value)
        j2_w = float(self.get_parameter("ik_j2_lift_weight").value)
        j2_pref = float(self.get_parameter("ik_j2_pref").value)
        j2_floor = float(self.get_parameter("ik_forward_j2_floor").value)
        lim_pen = float(self.get_parameter("ik_joint_limit_penalty").value)
        fk_w = float(self.get_parameter("ik_fk_after_clamp_weight").value)

        forward_mid = _is_forward_mid_probe(gx, gz)
        seeds: list[kdl.JntArray] = []
        # 前伸中等：勿把「当前关节」放第一个，否则 LMA 易从已缩团的 cur 收敛到塌肩解；先给抬肩/舒展初值。
        if forward_mid:
            seeds.append(_jnt_copy(ready_fallback))
            seeds.append(_upright_forward_seed())
            seeds.append(_mid_forward_probe_seed())
            seeds.append(_jnt_copy(_extended_reach_seed_templates()[0]))
        else:
            seeds.append(ready_fallback)

        seeds.append(cur)
        if self._have_last_q_success:
            seeds.append(_jnt_copy(self._last_q_success))
        seeds.extend(ext)
        if gz < low_seed_z:
            seeds.append(_low_reach_bias_seed())
        if not forward_mid and gx >= 0.32 and 0.34 <= gz <= 0.60:
            seeds.append(_mid_forward_probe_seed())
        if not forward_mid and gx >= 0.34 and 0.36 <= gz <= 0.58:
            seeds.append(_jnt_copy(_extended_reach_seed_templates()[0]))

        n_rnd = int(self.get_parameter("ik_num_random_seeds").value)
        for _ in range(max(0, n_rnd)):
            rnd = kdl.JntArray(7)
            for i in range(7):
                rnd[i] = float(self._q_seed[i]) + random.uniform(-0.2, 0.2)
            _clamp_fp3_jnt(rnd)
            seeds.append(rnd)

        q_tmp = kdl.JntArray(7)
        last_res = -100
        candidates: list[kdl.JntArray] = []
        for seed in seeds:
            res = self._ik.CartToJnt(seed, goal, q_tmp)
            last_res = res
            if res >= 0:
                candidates.append(_jnt_copy(q_tmp))

        if not candidates:
            return last_res, q_out

        if forward_mid:
            lifted = [
                q for q in candidates if float(_clamped_copy(q)[1]) > j2_floor
            ]
            if lifted:
                candidates = lifted
            else:
                # 所有解肩都过负：取最接近就绪肩角的一支，避免「最大 j2」把末端抬到指天
                best_up = min(
                    candidates,
                    key=lambda q: abs(float(_clamped_copy(q)[1]) - j2_pref),
                )
                for i in range(7):
                    q_out[i] = best_up[i]
                return 0, q_out

        def _pick_cost(q: kdl.JntArray) -> float:
            qc = _clamped_copy(q)
            c = _joint_blend_cost(qc, cur, ready_fallback, w) + _mid_forward_collapse_penalty(
                qc, gx, gz, pen_scale
            )
            c += lim_pen * _joint_limit_compression_penalty(qc, 1.0)
            c += fk_w * self._fk_position_err_sq(qc, goal)
            if forward_mid:
                dj = float(qc[1]) - j2_pref
                c += j2_w * (dj * dj)
            return c

        best = min(candidates, key=_pick_cost)
        for i in range(7):
            q_out[i] = best[i]
        # 不在此钳位：否则 _log_ik_diagnosis 用钳位后的 q 做 FK，会误报「差 >20mm」
        return 0, q_out

    def _log_ik_diagnosis(
        self,
        goal: kdl.Frame,
        q_ik_raw: kdl.JntArray,
        q_published: kdl.JntArray | None = None,
    ) -> None:
        """FK 用 IK 原始解核对；关节差分与 _last_published_q 用实际下发的 q（钳位后），避免误判。"""
        fk = kdl.Frame()
        if self._fk.JntToCart(q_ik_raw, fk) < 0:
            return
        ex = float(fk.p[0]) - float(goal.p[0])
        ey = float(fk.p[1]) - float(goal.p[1])
        ez = float(fk.p[2]) - float(goal.p[2])
        err = math.sqrt(ex * ex + ey * ey + ez * ez)
        self.get_logger().info(
            f"FK 核对 TCP(base): ({float(fk.p[0]):.3f},{float(fk.p[1]):.3f},{float(fk.p[2]):.3f}) "
            f"位置误差 {err * 1000:.1f} mm"
        )
        if err > 0.02:
            self.get_logger().warn(
                "末端位置与目标差 >20mm：请核对 frame_id=base、目标是否在可达空间、姿态是否过苛。"
            )
        qh = q_published if q_published is not None else q_ik_raw
        if self._last_published_q is not None:
            dq0 = abs(float(qh[0]) - self._last_published_q[0])
            dqrest = sum(
                abs(float(qh[i]) - self._last_published_q[i]) for i in range(1, 7)
            )
            if dq0 > 0.2 and dqrest < 0.15:
                self.get_logger().warn(
                    "本次解与上次相比几乎只有 joint1 变化大，运动易像水平面内转弯；"
                    "若期望前后探伸，请确认「收到末端目标」里 x/y/z 与预期一致，"
                    "或执行: ros2 run test_env publish_ee_goal <x> <y> <z>"
                )
        self._last_published_q = [float(qh[i]) for i in range(7)]

    def _on_joint_states(self, msg: JointState):
        if not msg.name or len(msg.name) != len(msg.position):
            return
        name_to_p = {n: float(p) for n, p in zip(msg.name, msg.position)}
        for i, name in enumerate(self.JOINT_NAMES):
            if name in name_to_p:
                self._q_seed[i] = name_to_p[name]
        _clamp_fp3_jnt(self._q_seed)

        if (
            self._waypoint_target is not None
            and self._waypoint_queue is not None
            and all(n in name_to_p for n in self.JOINT_NAMES)
        ):
            tol = float(self.get_parameter("waypoint_reach_tolerance_rad").value)
            err = max(
                abs(name_to_p[n] - self._waypoint_target[i])
                for i, n in enumerate(self.JOINT_NAMES)
            )
            if err <= tol:
                if self._waypoint_queue:
                    nxt = self._waypoint_queue.pop(0)
                    self._waypoint_target = nxt
                    q = kdl.JntArray(7)
                    for i in range(7):
                        q[i] = nxt[i]
                    self._publish_joint_array(q)
                    self.get_logger().info(
                        f"路径点推进，剩余 {len(self._waypoint_queue)} 段 (关节误差 {err:.3f} rad)"
                    )
                else:
                    self._waypoint_target = None
                    self._waypoint_queue = None
                    if self._pending_final_goal_frame is not None:
                        self._last_goal_frame = self._pending_final_goal_frame
                        self._pending_final_goal_frame = None
                    self.get_logger().info("笛卡尔分段路径完成")

    def _on_goal(self, msg: PoseStamped):
        self_do = msg.pose
        frame = (msg.header.frame_id or "base").strip()
        if not frame:
            frame = "base"

        if frame != "base":
            try:
                when = rclpy.time.Time()
                if msg.header.stamp.sec != 0 or msg.header.stamp.nanosec != 0:
                    when = rclpy.time.Time.from_msg(msg.header.stamp)
                tf_map = self._tf_buffer.lookup_transform(
                    "base", frame, when, timeout=rclpy.duration.Duration(seconds=0.5)
                )
                # do_transform_pose 第一个参数须为 geometry_msgs/Pose，不能传 PoseStamped
                self_do = do_transform_pose(msg.pose, tf_map)
            except Exception as ex:  # noqa: BLE001
                self.get_logger().error(f"TF base <- {frame}: {ex}")
                return

        _normalize_pose_orientation(self_do)
        self.get_logger().info(
            f"收到末端目标 (base 系): x={self_do.position.x:.4f} y={self_do.position.y:.4f} "
            f"z={self_do.position.z:.4f} (原始 frame_id={frame!r})"
        )

        goal = _pose_to_kdl_frame(self_do)
        gx_log = float(goal.p[0])
        gz_log = float(goal.p[2])
        ext_tpl = self._use_extended_seeds_for_goal(goal)
        fwd_mid = _is_forward_mid_probe(gx_log, gz_log)
        self.get_logger().info(
            f"IK 舒展模板(extended_reach): {'是' if ext_tpl else '否'}；"
            f"前伸中等额外种子(_solve_ik 内): {'是' if fwd_mid else '否'}"
        )
        if bool(self.get_parameter("skip_duplicate_cartesian").value):
            # 阈值过小会导致反复重解、关节微抖；过大则易误判「同目标」
            if _frame_near(goal, self._last_goal_frame, pos_eps=5e-4, ang_eps=0.04):
                self.get_logger().warn(
                    "忽略与上一成功目标几乎相同的 Cartesian（skip_duplicate_cartesian:=true）。"
                    "若你确实改了指令但位姿未变，请检查 ros2 topic pub 的 YAML 是否被正确解析，"
                    "或执行: ros2 param set /franka_fp3_ik_goal skip_duplicate_cartesian false"
                )
                return

        self._waypoint_queue = None
        self._waypoint_target = None
        self._pending_final_goal_frame = None

        use_path = bool(self.get_parameter("use_cartesian_path").value)
        steps = int(self.get_parameter("cartesian_path_steps").value)
        if use_path and steps >= 2:
            F_start = self._fk_frame(self._q_seed)
            if F_start is None:
                self.get_logger().warn("FK 失败，退回单次末端 IK")
                use_path = False
            else:
                wp: list[list[float]] = []
                q_prev = _jnt_copy(self._q_seed)
                failed = False
                q_first_raw: kdl.JntArray | None = None
                for k in range(1, steps + 1):
                    alpha = k / float(steps)
                    Fi = _interp_frame(F_start, goal, alpha)
                    for i in range(7):
                        self._q_seed[i] = q_prev[i]
                    res, q_out = self._solve_ik(Fi)
                    if res < 0:
                        self.get_logger().warn(
                            f"分段路径在 alpha={alpha:.2f} IK 失败，退回单次末端 IK: "
                            f"{self._ik.strError(res)}"
                        )
                        failed = True
                        break
                    if k == 1:
                        q_first_raw = _jnt_copy(q_out)
                    q_pub = _jnt_copy(q_out)
                    _clamp_fp3_jnt(q_pub)
                    wp.append([float(q_pub[i]) for i in range(7)])
                    for i in range(7):
                        q_prev[i] = q_pub[i]

                if not failed and wp:
                    self._pending_final_goal_frame = goal
                    self._waypoint_queue = wp[1:]
                    self._waypoint_target = wp[0]
                    q0 = kdl.JntArray(7)
                    for i in range(7):
                        q0[i] = wp[0][i]
                    for i in range(7):
                        self._last_q_success[i] = q0[i]
                    self._have_last_q_success = True
                    self._publish_joint_array(q0)
                    self.get_logger().info(
                        f"笛卡尔分段路径: {steps} 点，已发第 1 点；"
                        "末端将沿 base 系直线插值（关节仍由 interactive 平滑）"
                    )
                    self.get_logger().info(
                        "IK ok[1]: "
                        + ", ".join(f"{n}={p:.3f}" for n, p in zip(self.JOINT_NAMES, wp[0]))
                    )
                    f1 = _interp_frame(F_start, goal, 1.0 / float(steps))
                    if q_first_raw is not None:
                        q1p = _jnt_copy(q_first_raw)
                        _clamp_fp3_jnt(q1p)
                        self._log_ik_diagnosis(f1, q_first_raw, q1p)
                    return

        res, q_out = self._solve_ik(goal)
        if res < 0:
            zr = float(self_do.position.z)
            hint = ""
            if zr < 0.35:
                hint = (
                    " 提示: base 系 z 很低(如<0.35m)时 LMA 常失败或无可行解；可试略提高 z(如 0.35~0.45)，"
                    "或检查姿态四元数是否过苛。"
                )
            self.get_logger().error(
                f"IK 失败: {self._ik.strError(res)}；"
                f"请求位置 (base) x={self_do.position.x:.3f} y={self_do.position.y:.3f} z={self_do.position.z:.3f}。"
                "失败时不会发布 /franka_joint_target，机械臂会保持上一姿态。"
                + hint
            )
            return

        q_pub = _jnt_copy(q_out)
        _clamp_fp3_jnt(q_pub)
        self._log_ik_diagnosis(goal, q_out, q_pub)
        for i in range(7):
            self._q_seed[i] = q_pub[i]
            self._last_q_success[i] = q_pub[i]
        self._have_last_q_success = True
        self._last_goal_frame = goal

        self._publish_joint_array(q_pub)
        self.get_logger().info(
            "IK ok: "
            + ", ".join(
                f"{n}={float(q_pub[i]):.3f}" for i, n in enumerate(self.JOINT_NAMES)
            )
        )


def main():
    rclpy.init()
    node = FrankaFp3IkGoal()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    try:
        node.destroy_node()
    except Exception:
        pass
    try:
        rclpy.shutdown()
    except Exception:
        pass  # launch 可能已关掉 context，避免重复 rcl_shutdown 报错


if __name__ == "__main__":
    main()
