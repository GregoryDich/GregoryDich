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

juce_add_plugin(Tonamorph
    COMPANY_NAME "Tonamorph Audio"
    COMPANY_WEBSITE "https://tonamorph.com"
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
    PRODUCT_NAME "Tonamorph"
    VST3_CATEGORIES Instrument Sampler
    AU_MAIN_TYPE kAudioUnitType_MusicDevice)

juce_generate_juce_header(Tonamorph)

target_sources(Tonamorph
    PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginEditor.cpp
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
        Source/UI/TonamorphLookAndFeel.cpp)

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

target_link_libraries(Tonamorph
    PRIVATE
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
