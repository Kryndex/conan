from conans.test.utils.tools import TestClient
import unittest
from conans.paths import CONANFILE, BUILD_INFO
from conans.model.ref import PackageReference
import os
from conans.util.files import load


conanfile_scope_env = """
from conans import ConanFile

class AConan(ConanFile):
    requires = "Hello/0.1@lasote/testing"
    generators = "cmake"

    def build(self):
        self.output.info("INCLUDE PATH: %s" % self.deps_cpp_info.include_paths[0])
        self.output.info("HELLO ROOT PATH: %s" % self.deps_cpp_info["Hello"].rootpath)
        self.output.info("HELLO INCLUDE PATHS: %s" % self.deps_cpp_info["Hello"].include_paths[0])
"""

conanfile_dep = """
from conans import ConanFile
from conans.tools import mkdir
import os

class AConan(ConanFile):
    name = "Hello"
    version = "0.1"

    def package(self):
        mkdir(os.path.join(self.package_folder, "include"))
"""


class ConanBuildTest(unittest.TestCase):

    def build_error_test(self):
        """ If not using -g txt generator, and build() requires self.deps_cpp_info,
        or self.deps_user_info it wont fail because now it's automatic
        """
        client = TestClient()
        client.save({CONANFILE: conanfile_dep})
        client.run("export lasote/testing")
        client.save({CONANFILE: conanfile_scope_env}, clean_first=True)
        client.run("install --build=missing")
        client.run("build")  # We do not need to specify -g txt anymore
        self.assertTrue(os.path.exists(os.path.join(client.current_folder, BUILD_INFO)))

        conanfile_user_info = """
from conans import ConanFile

class AConan(ConanFile):
    requires = "Hello/0.1@lasote/testing"
    generators = "cmake"

    def build(self):
        self.deps_user_info
        self.deps_env_info
"""
        client.save({CONANFILE: conanfile_user_info}, clean_first=True)
        client.run("install --build=missing")
        client.run("build")

    def build_test(self):
        """ Try to reuse variables loaded from txt generator => deps_cpp_info
        """
        client = TestClient()
        client.save({CONANFILE: conanfile_dep})
        client.run("export lasote/testing")

        client.save({CONANFILE: conanfile_scope_env}, clean_first=True)
        client.run("install --build=missing")

        client.run("build")
        ref = PackageReference.loads("Hello/0.1@lasote/testing:"
                                     "5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9")
        package_folder = client.paths.package(ref).replace("\\", "/")
        self.assertIn("Project: INCLUDE PATH: %s/include" % package_folder, client.user_io.out)
        self.assertIn("Project: HELLO ROOT PATH: %s" % package_folder, client.user_io.out)
        self.assertIn("Project: HELLO INCLUDE PATHS: %s/include"
                      % package_folder, client.user_io.out)

    def build_dots_names_test(self):
        """ Try to reuse variables loaded from txt generator => deps_cpp_info
        """
        client = TestClient()
        conanfile_dep = """
from conans import ConanFile

class AConan(ConanFile):
    pass
"""
        client.save({CONANFILE: conanfile_dep})
        client.run("create Hello.Pkg/0.1@lasote/testing")
        client.run("create Hello-Tools/0.1@lasote/testing")
        conanfile_scope_env = """
from conans import ConanFile

class AConan(ConanFile):
    requires = "Hello.Pkg/0.1@lasote/testing", "Hello-Tools/0.1@lasote/testing"

    def build(self):
        self.output.info("HELLO ROOT PATH: %s" % self.deps_cpp_info["Hello.Pkg"].rootpath)
        self.output.info("HELLO ROOT PATH: %s" % self.deps_cpp_info["Hello-Tools"].rootpath)
"""
        client.save({CONANFILE: conanfile_scope_env}, clean_first=True)
        client.run("install --build=missing")
        client.run("build")
        self.assertIn("Hello.Pkg/0.1/lasote/testing", client.out)
        self.assertIn("Hello-Tools/0.1/lasote/testing", client.out)

    def build_cmake_install_test(self):
        client = TestClient()
        conanfile = """
from conans import ConanFile, CMake

class AConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.install()
"""
        cmake = """set(CMAKE_CXX_COMPILER_WORKS 1)
project(Chat NONE)
cmake_minimum_required(VERSION 2.8.12)

        install(FILES header.h DESTINATION include)
"""
        client.save({CONANFILE: conanfile,
                     "CMakeLists.txt": cmake,
                     "header.h": "my header h!!"})
        client.run("install")
        error = client.run("build", ignore_error=True)
        self.assertTrue(error)
        self.assertIn("CMAKE_INSTALL_PREFIX not defined for 'cmake.install()'",
                      client.user_io.out)
        client.run("build -pf=mypkg")
        header = load(os.path.join(client.current_folder, "mypkg/include/header.h"))
        self.assertEqual(header, "my header h!!")

    def build_with_deps_env_info_test(self):
        client = TestClient()
        conanfile = """
from conans import ConanFile, CMake

class AConan(ConanFile):
    name = "lib"
    version = "1.0"
    
    def package_info(self):
        self.env_info.MYVAR = "23"
    
"""
        client.save({CONANFILE: conanfile})
        client.run("export lasote/stable")

        conanfile = """
from conans import ConanFile

class AConan(ConanFile):
    requires = "lib/1.0@lasote/stable"
    
    def build(self):
        assert(self.deps_env_info["lib"].MYVAR == "23")
    
"""
        client.save({CONANFILE: conanfile}, clean_first=True)
        client.run("install . --build missing")
        client.run("build .")
