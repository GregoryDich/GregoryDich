# JUCE-free unit tests for plugin/Source/Core. The executable only sees the
# Source/ include directory, which guarantees that Core headers never pull in
# JUCE (they would fail to compile here if they did).

file(GLOB TONAMORPH_TEST_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp")

add_executable(tonamorph_core_tests ${TONAMORPH_TEST_SOURCES})

target_include_directories(tonamorph_core_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/../Source)

target_compile_features(tonamorph_core_tests PRIVATE cxx_std_20)

# test_strings.cpp scans Source/ for product-name literals; test_demo_manifest.cpp reads the
# demo morph generated at configure time (TONAMORPH_DEMO_DIR, set by the parent).
target_compile_definitions(tonamorph_core_tests
    PRIVATE
        TONAMORPH_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../Source"
        $<$<BOOL:${TONAMORPH_DEMO_DIR}>:TONAMORPH_DEMO_DIR="${TONAMORPH_DEMO_DIR}">)

if(MSVC)
    target_compile_options(tonamorph_core_tests PRIVATE /W4)
else()
    target_compile_options(tonamorph_core_tests PRIVATE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)
endif()

add_test(NAME tonamorph_core_tests COMMAND tonamorph_core_tests)
