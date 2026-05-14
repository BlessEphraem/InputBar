cmake_minimum_required(VERSION 3.10)

if(NOT PROJECT_VERSION)
    message(FATAL_ERROR "PROJECT_VERSION non defini. Lancez le build via build/build_app.bat.")
endif()

project(InputBar VERSION ${PROJECT_VERSION})

# §11 — Racine du depot (deux niveaux au-dessus de build/configuration/)
set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
set(SRC_DIR   "${REPO_ROOT}/src")

# Lire les metadonnees depuis la source de verite unique
file(READ "${REPO_ROOT}/build/project.json" _PROJECT_JSON)
string(JSON _APP_NAME    GET ${_PROJECT_JSON} name)
string(JSON _APP_PUBLISHER GET ${_PROJECT_JSON} publisher)
string(JSON _GITHUB_REPO GET ${_PROJECT_JSON} github_repo)

if(NOT APP_NAME)
    set(APP_NAME "${_APP_NAME}")
endif()
if(NOT APP_PUBLISHER)
    set(APP_PUBLISHER "${_APP_PUBLISHER}")
endif()

set(DIST_DIR     "${REPO_ROOT}/build_dist")
set(PYI_WORK_DIR "${REPO_ROOT}/build_pyinstaller")

# Genere _version.py depuis le template
configure_file(
    "${SRC_DIR}/_version.py.in"
    "${SRC_DIR}/_version.py"
    @ONLY
)

if(NOT RELEASES_DIR)
    set(RELEASES_DIR "releases")
endif()
set(FULL_RELEASES_DIR "${REPO_ROOT}/${RELEASES_DIR}")

find_program(PYINSTALLER_EXE NAMES pyinstaller)
if(NOT PYINSTALLER_EXE)
    message(FATAL_ERROR "PyInstaller non trouve. Installez-le avec 'pip install pyinstaller'.")
endif()

option(GENERATE_SETUP "Generer l'installateur Setup.exe ?" OFF)

message(STATUS "------------------------------------------------------")
message(STATUS "Build: ${APP_NAME} v${PROJECT_VERSION} (${APP_PUBLISHER})")
message(STATUS "Destination: ${FULL_RELEASES_DIR}")
message(STATUS "------------------------------------------------------")

# --- CIBLE 1 : BUILD PRINCIPAL ---
add_custom_target(build_app
    COMMAND ${CMAKE_COMMAND} -E remove_directory "${DIST_DIR}"
    COMMAND ${CMAKE_COMMAND} -E remove_directory "${PYI_WORK_DIR}"
    COMMAND "${PYINSTALLER_EXE}" --noconfirm
            --distpath "${DIST_DIR}"
            --workpath "${PYI_WORK_DIR}"
            "${REPO_ROOT}/build/InputBar.spec"
    COMMAND python -c "import pathlib, shutil; [p.unlink() for p in pathlib.Path('${DIST_DIR}').rglob('*.pyc')]; [shutil.rmtree(p) for p in pathlib.Path('${DIST_DIR}').rglob('__pycache__')]"
    COMMAND python -c "import pathlib, shutil, sys; src = sorted(pathlib.Path('${REPO_ROOT}/../../Daemons/WinKeyHook/releases').glob('WinKeyHook_v*_Setup.exe')); lib = pathlib.Path('${DIST_DIR}/${APP_NAME}/Lib'); lib.mkdir(parents=True, exist_ok=True); (shutil.copy2(str(src[-1]), str(lib / 'WinKeyHook_setup.exe')) if src else sys.exit('No WinKeyHook_v*_Setup.exe found'))"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${FULL_RELEASES_DIR}"
    COMMAND ${CMAKE_COMMAND} -E chdir "${DIST_DIR}" ${CMAKE_COMMAND} -E tar "cfv" "${FULL_RELEASES_DIR}/${APP_NAME}_v${PROJECT_VERSION}_Portable.zip" --format=zip "${APP_NAME}"
    WORKING_DIRECTORY "${REPO_ROOT}"
    COMMENT "Phase 1 : Compilation PyInstaller et creation du ZIP portable..."
)

# --- CIBLE 2 : INNO SETUP ---
if(GENERATE_SETUP)
    find_program(ISCC_EXE NAMES ISCC
                 PATHS "C:/Program Files (x86)/Inno Setup 6"
                       "C:/Program Files/Inno Setup 6")

    if(ISCC_EXE)
        add_custom_target(generate_setup
            DEPENDS build_app
            COMMAND "${ISCC_EXE}"
                    "/DAppName=${APP_NAME}"
                    "/DAppVersion=${PROJECT_VERSION}"
                    "/DAppPublisher=${APP_PUBLISHER}"
                    "/DAppExeName=${APP_NAME}.exe"
                    "/DAppId=${APP_GUID}"
                    "/O${FULL_RELEASES_DIR}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/setup_script.iss"
            WORKING_DIRECTORY "${REPO_ROOT}"
            COMMENT "Phase 2 : Generation de l'installateur Setup.exe dans ${RELEASES_DIR}..."
        )
    else()
        message(WARNING "Inno Setup (ISCC.exe) non trouve. L'installateur ne sera pas genere.")
    endif()
endif()
