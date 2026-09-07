cmake_minimum_required(VERSION 3.22)

project(SnapPlayAI VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(SNAPPLAY_USE_RUBBERBAND "Use Rubber Band Library for high-quality offline pitch shifting" ON)
option(SNAPPLAY_BUILD_TESTS "Build the JUCE-free core test executable" ON)

# ---------------------------------------------------------------------------
# JUCE: prefer a local checkout (JUCE_SOURCE_DIR or /home/user/deps/JUCE),
# otherwise fetch the pinned release from GitHub.
# ---------------------------------------------------------------------------
if(NOT DEFINED JUCE_SOURCE_DIR AND EXISTS "/home/user/deps/JUCE/CMakeLists.txt")
    set(JUCE_SOURCE_DIR "/home/user/deps/JUCE")
endif()

if(DEFINED JUCE_SOURCE_DIR AND EXISTS "${JUCE_SOURCE_DIR}/CMakeLists.txt")
    message(STATUS "SnapPlay: using JUCE from ${JUCE_SOURCE_DIR}")
    add_subdirectory("${JUCE_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/juce" EXCLUDE_FROM_ALL)
else()
    message(STATUS "SnapPlay: fetching JUCE 8.0.8")
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
set(SNAPPLAY_FORMATS VST3 Standalone)
if(APPLE)
    list(APPEND SNAPPLAY_FORMATS AU)
endif()

juce_add_plugin(SnapPlayAI
    COMPANY_NAME "SnapPlay"
    COMPANY_WEBSITE "https://snapplay.ai"
    BUNDLE_ID "ai.snapplay.plugin"
    PLUGIN_MANUFACTURER_CODE Snpl
    PLUGIN_CODE Snap
    FORMATS ${SNAPPLAY_FORMATS}
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE
    PRODUCT_NAME "SnapPlay AI"
    VST3_CATEGORIES Instrument Sampler
    AU_MAIN_TYPE kAudioUnitType_MusicDevice)

juce_generate_juce_header(SnapPlayAI)

target_sources(SnapPlayAI
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
        Source/Export/DragExport.cpp)

target_include_directories(SnapPlayAI
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/Source)

target_compile_definitions(SnapPlayAI
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=1
        JUCE_VST3_CAN_REPLACE_VST2=0
        JUCE_DISPLAY_SPLASH_SCREEN=0
        JUCE_MODAL_LOOPS_PERMITTED=0
        SNAPPLAY_VERSION_STRING="${PROJECT_VERSION}")

target_link_libraries(SnapPlayAI
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
# Optional Rubber Band (offline high-quality pitch shifting)
# ---------------------------------------------------------------------------
if(SNAPPLAY_USE_RUBBERBAND)
    find_package(PkgConfig QUIET)
    if(PkgConfig_FOUND)
        pkg_check_modules(RUBBERBAND IMPORTED_TARGET rubberband)
    endif()

    if(RUBBERBAND_FOUND)
        message(STATUS "SnapPlay: Rubber Band ${RUBBERBAND_VERSION} found - high-quality pitch shifting enabled")
        target_compile_definitions(SnapPlayAI PUBLIC SNAPPLAY_HAS_RUBBERBAND=1)
        target_link_libraries(SnapPlayAI PRIVATE PkgConfig::RUBBERBAND)
    else()
        message(WARNING "SnapPlay: Rubber Band not found via pkg-config - falling back to resampling pitch shift")
        target_compile_definitions(SnapPlayAI PUBLIC SNAPPLAY_HAS_RUBBERBAND=0)
    endif()
else()
    target_compile_definitions(SnapPlayAI PUBLIC SNAPPLAY_HAS_RUBBERBAND=0)
endif()

# ---------------------------------------------------------------------------
# JUCE-free core tests
# ---------------------------------------------------------------------------
if(SNAPPLAY_BUILD_TESTS)
    enable_testing()
    add_subdirectory(Tests)
endif()
