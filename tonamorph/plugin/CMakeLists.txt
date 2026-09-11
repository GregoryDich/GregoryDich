cmake_minimum_required(VERSION 3.22)

# Release builds pass the git tag through packaging/ (-DTONAMORPH_VERSION=X.Y.Z);
# everything else uses this default.
set(TONAMORPH_VERSION "0.1.0" CACHE STRING "Plugin version (X.Y.Z)")
project(Tonamorph VERSION ${TONAMORPH_VERSION} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(TONAMORPH_USE_RUBBERBAND "Use Rubber Band Library for high-quality offline pitch shifting" ON)
option(TONAMORPH_BUILD_TESTS "Build the JUCE-free core test executable" ON)

# ---------------------------------------------------------------------------
# JUCE: prefer a local checkout (JUCE_SOURCE_DIR or /home/user/deps/JUCE),
# otherwise fetch the pinned release from GitHub.
# ---------------------------------------------------------------------------
if(NOT DEFINED JUCE_SOURCE_DIR AND EXISTS "/home/user/deps/JUCE/CMakeLists.txt")
    set(JUCE_SOURCE_DIR "/home/user/deps/JUCE")
endif()

if(DEFINED JUCE_SOURCE_DIR AND EXISTS "${JUCE_SOURCE_DIR}/CMakeLists.txt")
    message(STATUS "Tonamorph: using JUCE from ${JUCE_SOURCE_DIR}")
    add_subdirectory("${JUCE_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/juce" EXCLUDE_FROM_ALL)
else()
    message(STATUS "Tonamorph: fetching JUCE 8.0.8")
    include(FetchContent)
    FetchContent_Declare(JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG        8.0.8
        GIT_SHALLOW    TRUE)
    FetchContent_MakeAvailable(JUCE)
endif()

# ---------------------------------------------------------------------------
# Plugin target
# ---------------------------------------------------------------------------
set(TONAMORPH_FORMATS VST3 Standalone)
if(APPLE)
    list(APPEND TONAMORPH_FORMATS AU)
endif()

# Product identity (keep in sync with packaging/product.env); also fills the [[PRODUCT_NAME]] /
# [[WEBSITE_URL]] placeholders of the embedded third-party notices below.
set(TONAMORPH_PRODUCT_NAME "Tonamorph")
set(TONAMORPH_COMPANY_WEBSITE "https://tonamorph.com")

juce_add_plugin(Tonamorph
    COMPANY_NAME "Tonamorph Audio"
    COMPANY_WEBSITE "${TONAMORPH_COMPANY_WEBSITE}"
    BUNDLE_ID "com.tonamorph.plugin"
    PLUGIN_MANUFACTURER_CODE Tona
    PLUGIN_CODE Mrph
    FORMATS ${TONAMORPH_FORMATS}
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE
    PRODUCT_NAME "${TONAMORPH_PRODUCT_NAME}"
    VST3_CATEGORIES Instrument Sampler
    AU_MAIN_TYPE kAudioUnitType_MusicDevice)

juce_generate_juce_header(Tonamorph)

target_sources(Tonamorph
    PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginEditor.cpp
        Source/App/CrashReporter.cpp
        Source/App/DemoMorph.cpp
        Source/App/PluginSettings.cpp
        Source/Cloud/ApiClient.cpp
        Source/Cloud/Models.cpp
        Source/Cloud/AuthManager.cpp
        Source/Cloud/JobClient.cpp
        Source/Cloud/UploadEncoder.cpp
        Source/Engine/SamplerEngine.cpp
        Source/Engine/StemSound.cpp
        Source/Engine/StemVoice.cpp
        Source/Engine/PitchShifter.cpp
        Source/Engine/DrumKit.cpp
        Source/Engine/ScaleLockProcessor.cpp
        Source/Export/MidiExporter.cpp
        Source/Export/FscExporter.cpp
        Source/Export/DragExport.cpp
        Source/UI/AboutOverlay.cpp
        Source/UI/FeedbackBar.cpp
        Source/UI/MessageToast.cpp
        Source/UI/NpsCard.cpp
        Source/UI/ReferralPanel.cpp
        Source/UI/ScaleKeyboard.cpp
        Source/UI/TonamorphLookAndFeel.cpp
        Source/UI/VersionBanner.cpp)

target_include_directories(Tonamorph
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/Source)

target_compile_definitions(Tonamorph
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=1
        JUCE_VST3_CAN_REPLACE_VST2=0
        JUCE_DISPLAY_SPLASH_SCREEN=0
        JUCE_MODAL_LOOPS_PERMITTED=0
        TONAMORPH_VERSION_STRING="${PROJECT_VERSION}")

# ---------------------------------------------------------------------------
# Bundled demo morph: generated deterministically at configure time by
# Resources/generate_demo.py (numpy; soundfile optional) into the build tree and
# embedded as DemoData::*. The plugin installs it into its job cache as job "demo".
# ---------------------------------------------------------------------------
find_package(Python3 COMPONENTS Interpreter QUIET)
if(NOT Python3_Interpreter_FOUND)
    message(FATAL_ERROR "Tonamorph: python3 with numpy is required to generate the bundled demo morph")
endif()

set(TONAMORPH_DEMO_DIR "${CMAKE_BINARY_DIR}/demo")
set(TONAMORPH_DEMO_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/Resources/generate_demo.py")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${TONAMORPH_DEMO_SCRIPT}")

execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${TONAMORPH_DEMO_SCRIPT}" "${TONAMORPH_DEMO_DIR}"
    RESULT_VARIABLE tonamorph_demo_result
    OUTPUT_VARIABLE tonamorph_demo_output
    ERROR_VARIABLE tonamorph_demo_error)

if(NOT tonamorph_demo_result EQUAL 0)
    message(FATAL_ERROR "Tonamorph: demo morph generation failed (needs `pip install numpy`):\n${tonamorph_demo_output}${tonamorph_demo_error}")
endif()
string(STRIP "${tonamorph_demo_output}" tonamorph_demo_output)
message(STATUS "Tonamorph: ${tonamorph_demo_output}")

# ---------------------------------------------------------------------------
# Third-party notices for the About screen (THIRD_PARTY_LICENSES.md, action 8): rendered
# to plain text at configure time by packaging/common/eula_to_txt.py — the converter the
# installers use — and embedded next to the demo morph as DemoData::third_party_notices_txt.
# [[PRODUCT_NAME]] and [[WEBSITE_URL]] are filled from this file; the company placeholders
# come from the environment when a release build sets them and stay in the text verbatim
# otherwise (--keep-unresolved). The file is only rewritten when its bytes change.
# ---------------------------------------------------------------------------
set(TONAMORPH_NOTICES_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../THIRD_PARTY_LICENSES.md")
set(TONAMORPH_NOTICES_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/packaging/common/eula_to_txt.py")
set(TONAMORPH_NOTICES_FILE "${CMAKE_BINARY_DIR}/notices/third_party_notices.txt")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${TONAMORPH_NOTICES_SOURCE}" "${TONAMORPH_NOTICES_SCRIPT}")

if(NOT DEFINED ENV{PRODUCT_NAME})
    set(ENV{PRODUCT_NAME} "${TONAMORPH_PRODUCT_NAME}")
endif()
if(NOT DEFINED ENV{WEBSITE_URL})
    set(ENV{WEBSITE_URL} "${TONAMORPH_COMPANY_WEBSITE}")
endif()

execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${TONAMORPH_NOTICES_SCRIPT}"
            "${TONAMORPH_NOTICES_SOURCE}" "${TONAMORPH_NOTICES_FILE}.new"
            --missing-ok --keep-unresolved --placeholder-title "Third-Party Notices"
    RESULT_VARIABLE tonamorph_notices_result
    OUTPUT_VARIABLE tonamorph_notices_output
    ERROR_VARIABLE tonamorph_notices_error)

if(NOT tonamorph_notices_result EQUAL 0)
    message(FATAL_ERROR "Tonamorph: rendering the third-party notices failed:\n${tonamorph_notices_output}${tonamorph_notices_error}")
endif()

execute_process(COMMAND "${CMAKE_COMMAND}" -E copy_if_different
                        "${TONAMORPH_NOTICES_FILE}.new" "${TONAMORPH_NOTICES_FILE}")
file(REMOVE "${TONAMORPH_NOTICES_FILE}.new")
file(SIZE "${TONAMORPH_NOTICES_FILE}" tonamorph_notices_bytes)

if(tonamorph_notices_bytes GREATER 204800)
    message(FATAL_ERROR "Tonamorph: the third-party notices are ${tonamorph_notices_bytes} bytes; the embedded text must stay under 200 KB")
endif()
message(STATUS "Tonamorph: third-party notices ${tonamorph_notices_bytes} bytes")

juce_add_binary_data(TonamorphDemoData
    NAMESPACE DemoData
    HEADER_NAME DemoData.h
    SOURCES
        "${TONAMORPH_DEMO_DIR}/bass.wav"
        "${TONAMORPH_DEMO_DIR}/drums.wav"
        "${TONAMORPH_DEMO_DIR}/other.wav"
        "${TONAMORPH_DEMO_DIR}/vocals.wav"
        "${TONAMORPH_DEMO_DIR}/score.mid"
        "${TONAMORPH_DEMO_DIR}/result.json"
        "${TONAMORPH_NOTICES_FILE}")

target_link_libraries(Tonamorph
    PRIVATE
        TonamorphDemoData
        juce::juce_audio_utils
        juce::juce_audio_processors
        juce::juce_audio_formats
        juce::juce_dsp
        juce::juce_gui_extra
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)

# ---------------------------------------------------------------------------
# libcurl: JUCE_USE_CURL=1 makes juce_core call libcurl directly on Linux, but the
# JUCE module system does not add the library itself.
# ---------------------------------------------------------------------------
if(UNIX AND NOT APPLE)
    find_package(CURL QUIET)
    if(CURL_FOUND)
        target_link_libraries(Tonamorph PRIVATE CURL::libcurl)
    else()
        find_package(PkgConfig REQUIRED)
        pkg_check_modules(LIBCURL REQUIRED IMPORTED_TARGET libcurl)
        target_link_libraries(Tonamorph PRIVATE PkgConfig::LIBCURL)
    endif()
endif()

# ---------------------------------------------------------------------------
# Optional Rubber Band (offline high-quality pitch shifting)
# ---------------------------------------------------------------------------
if(TONAMORPH_USE_RUBBERBAND)
    find_package(PkgConfig QUIET)
    if(PkgConfig_FOUND)
        pkg_check_modules(RUBBERBAND IMPORTED_TARGET rubberband)
    endif()

    if(RUBBERBAND_FOUND)
        message(STATUS "Tonamorph: Rubber Band ${RUBBERBAND_VERSION} found - high-quality pitch shifting enabled")
        target_compile_definitions(Tonamorph PUBLIC TONAMORPH_HAS_RUBBERBAND=1)
        target_link_libraries(Tonamorph PRIVATE PkgConfig::RUBBERBAND)
    else()
        message(WARNING "Tonamorph: Rubber Band not found via pkg-config - falling back to resampling pitch shift")
        target_compile_definitions(Tonamorph PUBLIC TONAMORPH_HAS_RUBBERBAND=0)
    endif()
else()
    target_compile_definitions(Tonamorph PUBLIC TONAMORPH_HAS_RUBBERBAND=0)
endif()

# ---------------------------------------------------------------------------
# JUCE-free core tests
# ---------------------------------------------------------------------------
if(TONAMORPH_BUILD_TESTS)
    enable_testing()
    add_subdirectory(Tests)
endif()
