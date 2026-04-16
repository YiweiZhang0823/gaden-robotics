# if we already have gaden, we're done
# otherwise, download it from git
find_package(gaden QUIET)
if(NOT TARGET gaden)
    FetchContent_Declare(
        gaden
        GIT_REPOSITORY git@github.com:MAPIRlab/gaden_core.git
        GIT_TAG main
    )
    
    FetchContent_GetProperties(gaden)
    if(NOT gaden_POPULATED)
        FetchContent_Populate(gaden)
        add_subdirectory(${gaden_SOURCE_DIR})
    endif()
endif()
