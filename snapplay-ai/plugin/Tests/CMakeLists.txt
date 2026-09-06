# JUCE-free unit tests for plugin/Source/Core. The executable only sees the
# Source/ include directory, which guarantees that Core headers never pull in
# JUCE (they would fail to compile here if they did).

file(GLOB SNAPPLAY_TEST_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp")

add_executable(snapplay_core_tests ${SNAPPLAY_TEST_SOURCES})

target_include_directories(snapplay_core_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/../Source)

target_compile_features(snapplay_core_tests PRIVATE cxx_std_20)

if(MSVC)
    target_compile_options(snapplay_core_tests PRIVATE /W4)
else()
    target_compile_options(snapplay_core_tests PRIVATE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)
endif()

add_test(NAME snapplay_core_tests COMMAND snapplay_core_tests)
