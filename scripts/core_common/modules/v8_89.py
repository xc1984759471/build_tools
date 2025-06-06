#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')
import config
import base
import os
import subprocess
import shutil
import platform

def change_bootstrap():
  base.move_file("./depot_tools/bootstrap/manifest.txt", "./depot_tools/bootstrap/manifest.txt.bak")
  content = "# changed by build_tools\n\n"
  content += "$VerifiedPlatform windows-amd64 windows-arm64 linux-amd64 mac-amd64 mac-arm64\n\n"

  content += "@Subdir python\n"
  content += "infra/3pp/tools/cpython/${platform} version:2@2.7.18.chromium.39\n\n"

  content += "@Subdir python3\n"
  content += "infra/3pp/tools/cpython3/${platform} version:2@3.8.10.chromium.23\n\n"

  content += "@Subdir git\n"
  content += "infra/3pp/tools/git/${platform} version:2@2.41.0.chromium.11\n"

  base.writeFile("./depot_tools/bootstrap/manifest.txt", content)
  return

def make_args(args, platform, is_64=True, is_debug=False):
  args_copy = args[:]
  if not base.is_os_arm():
    if is_64:
      args_copy.append("target_cpu=\\\"x64\\\"")
      args_copy.append("v8_target_cpu=\\\"x64\\\"")
    else:
      args_copy.append("target_cpu=\\\"x86\\\"")
      args_copy.append("v8_target_cpu=\\\"x86\\\"")
  else:
    args_copy = args[:]
    args_copy.append("target_cpu=\\\"arm64\\\"")
    args_copy.append("v8_target_cpu=\\\"arm64\\\"")
    args_copy.append("use_sysroot=true")
  if is_debug:
    args_copy.append("is_debug=true")
    if (platform == "windows"):
      args_copy.append("enable_iterator_debugging=true")
  else:
    args_copy.append("is_debug=false")
  
  if (platform == "linux"):
    args_copy.append("is_clang=true")
    if base.is_os_arm():
      args_copy.append("use_sysroot=false")
  if (platform == "windows"):
    args_copy.append("is_clang=false")

  return "--args=\"" + " ".join(args_copy) + "\""

def ninja_windows_make(args, is_64=True, is_debug=False):
  directory_out = "out.gn/"
  directory_out += ("win_64/" if is_64 else "win_32/")
  directory_out += ("debug" if is_debug else "release")

  base.cmd2("gn", ["gen", directory_out, make_args(args, "windows", is_64, is_debug)])
  base.copy_file("./" + directory_out + "/obj/v8_wrappers.ninja", "./" + directory_out + "/obj/v8_wrappers.ninja.bak")
  base.replaceInFile("./" + directory_out + "/obj/v8_wrappers.ninja", "target_output_name = v8_wrappers", "target_output_name = v8_wrappers\nbuild obj/v8_wrappers.obj: cxx ../../../src/base/platform/wrappers.cc")
  base.replaceInFile("./" + directory_out + "/obj/v8_wrappers.ninja", "build obj/v8_wrappers.lib: alink", "build obj/v8_wrappers.lib: alink obj/v8_wrappers.obj")

  win_toolset_wrapper_file = "build/toolchain/win/tool_wrapper.py"
  win_toolset_wrapper_file_content = base.readFile("build/toolchain/win/tool_wrapper.py")
  if (-1 == win_toolset_wrapper_file_content.find("line = line.decode('utf8')")):
    base.replaceInFile(win_toolset_wrapper_file, "for line in link.stdout:\n", "for line in link.stdout:\n      line = line.decode('utf8')\n")

  base.cmd("ninja", ["-C", directory_out, "v8_wrappers"])
  base.cmd("ninja", ["-C", directory_out])
  base.delete_file("./" + directory_out + "/obj/v8_wrappers.ninja")
  base.move_file("./" + directory_out + "/obj/v8_wrappers.ninja.bak", "./" + directory_out + "/obj/v8_wrappers.ninja")
  return

# patch v8 for build ---------------------------------------------------
def patch_windows_debug():
  # v8 8.9 version does not built with enable_iterator_debugging flag
  # patch heap.h file:
  file_patch = "./src/heap/heap.h"
  base.copy_file(file_patch, file_patch + ".bak")
  content_old = base.readFile(file_patch)
  posStart = content_old.find("class StrongRootBlockAllocator {")
  posEnd = content_old.find("};", posStart + 1)
  posEnd = content_old.find("};", posEnd + 1)
  content = content_old[0:posStart]
  content += base.readFile("./../../../../../build_tools/scripts/core_common/modules/v8_89.patch")
  content += content_old[posEnd + 2:]
  base.writeFile(file_patch, content)
  return

def unpatch_windows_debug():
  file_patch = "./src/heap/heap.h"
  base.move_file(file_patch + ".bak", file_patch)
  return
  
def create_symlink(src, dest):
  if not os.path.exists(dest):
    base.cmd("sudo", ["ln","-s", src, dest])


def is_package_installed(package_name):
  process = subprocess.Popen(["dpkg", "-s", package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = process.communicate()
  return process.returncode == 0
def install_clang():
    # Check if the packages are already installed
    packages = ["clang-12", "lld-12", "x11-utils", "llvm-12"]
    if all(is_package_installed(pkg) for pkg in packages):
        print("clang-12, lld-12, x11-utils, llvm-12 required packages are already installed.")
        for binary in binaries:
            create_symlink("/usr/bin/" + binary + "-12", "/usr/bin/" + binary)
        return True
    print("Clang++ Installing...")
    try:
        # see website how config https://apt.llvm.org/
        subprocess.check_call("wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -", shell=True)
        subprocess.check_call("echo \"deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-12 main\" | sudo tee /etc/apt/sources.list.d/llvm.list",shell=True)
        subprocess.check_call(["sudo", "apt-get", "update"])
        subprocess.check_call(["sudo", "apt-get", "install", "-y", "clang-12", "lld-12", "x11-utils", "llvm-12"])
        
        binaries = [
            "clang", "clang-cpp", "clang++", "dsymutil", "llc", "lli", "lli-child-target",
            "llvm-PerfectShuffle", "llvm-addr2line", "llvm-ar", "llvm-as", "llvm-bcanalyzer",
            "llvm-c-test", "llvm-cat", "llvm-cfi-verify", "llvm-config", "llvm-cov",
            "llvm-cvtres", "llvm-cxxdump", "llvm-cxxfilt", "llvm-cxxmap", "llvm-diff",
            "llvm-dis", "llvm-dlltool", "llvm-dwarfdump", "llvm-dwp", "llvm-elfabi",
            "llvm-exegesis", "llvm-extract", "llvm-ifs", "llvm-install-name-tool",
            "llvm-jitlink", "llvm-lib", "llvm-link", "llvm-lipo", "llvm-lto", "llvm-lto2",
            "llvm-mc", "llvm-mca", "llvm-modextract", "llvm-mt", "llvm-nm", "llvm-objcopy",
            "llvm-objdump", "llvm-opt-report", "llvm-pdbutil", "llvm-profdata", "llvm-ranlib",
            "llvm-rc", "llvm-readelf", "llvm-readobj", "llvm-reduce", "llvm-rtdyld",
            "llvm-size", "llvm-split", "llvm-stress", "llvm-strings", "llvm-strip",
            "llvm-symbolizer", "llvm-tblgen", "llvm-undname", "llvm-xray", "not", "obj2yaml",
            "opt", "verify-uselistorder", "sanstats", "yaml-bench", "yaml2obj", "ld.lld",
            "lld", "ld64.lld", "lld-link"
        ]
        
        for binary in binaries:
            create_symlink("/usr/bin/" + binary + "-12", "/usr/bin/" + binary)
        
        print("Clang++ installed successfully.")
    
    except subprocess.CalledProcessError as e:
        print("Failed to install clang: ",e)
        print("errout:",e.output)
        print("errcode:",e.returncode)
        return False
    
    return True

def update_gcc_version():
  base.cmd("sudo",["add-apt-repository", "ppa:ubuntu-toolchain-r/test"])
  base.cmd("sudo",["apt-get", "update"])
  base.cmd("sudo",["apt-get", "install", "gcc-10", "g++-10"])
  base.cmd("sudo",["update-alternatives", "--install", "/usr/bin/gcc", "gcc", "/usr/bin/gcc-10", "60", "--slave", "/usr/bin/g++", "g++", "/usr/bin/g++-10"])
  base.cmd("sudo",["update-alternatives", "--config", "gcc"])
  return
# ----------------------------------------------------------------------
def make():
  old_env = dict(os.environ)
  old_cur = os.getcwd()

  base_dir = base.get_script_dir() + "/../../core/Common/3dParty/v8_89"
  if not base.is_dir(base_dir):
    base.create_dir(base_dir)

  os.chdir(base_dir)
  if not base.is_dir("depot_tools"):
    base.cmd("git", ["clone", "https://chromium.googlesource.com/chromium/tools/depot_tools.git"])
    change_bootstrap()

  os.environ["PATH"] = base_dir + "/depot_tools" + os.pathsep + os.environ["PATH"]

  if ("windows" == base.host_platform()):
    base.set_env("DEPOT_TOOLS_WIN_TOOLCHAIN", "0")
    base.set_env("GYP_MSVS_VERSION", config.option("vs-version"))

  if not base.is_dir("v8"):
    base.cmd("./depot_tools/fetch", ["v8"], True)
    base.copy_dir("./v8/third_party", "./v8/third_party_new")
    if ("windows" == base.host_platform()):
      os.chdir("v8")
      base.cmd("git", ["config", "--system", "core.longpaths", "true"])
      os.chdir("../")
    v8_branch_version = "remotes/branch-heads/8.9"
    if ("mac" == base.host_platform()):
      v8_branch_version = "remotes/branch-heads/9.9"
    base.cmd("./depot_tools/gclient", ["sync", "-r", v8_branch_version], True)
    base.cmd("gclient", ["sync", "--force"], True)
    base.copy_dir("./v8/third_party_new/ninja", "./v8/third_party/ninja")

  if ("windows" == base.host_platform()):
    base.replaceInFile("v8/build/config/win/BUILD.gn", ":static_crt", ":dynamic_crt")
    if not base.is_file("v8/src/base/platform/wrappers.cc"):
      base.writeFile("v8/src/base/platform/wrappers.cc", "#include \"src/base/platform/wrappers.h\"\n")
  else:
    base.replaceInFile("depot_tools/gclient_paths.py", "@functools.lru_cache", "")

  if not base.is_file("v8/third_party/jinja2/tests.py.bak"):
    base.copy_file("v8/third_party/jinja2/tests.py", "v8/third_party/jinja2/tests.py.bak")
    base.replaceInFile("v8/third_party/jinja2/tests.py", "from collections import Mapping", "try:\n    from collections.abc import Mapping\nexcept ImportError:\n    from collections import Mapping")

  os.chdir("v8")
  
  gn_args = ["v8_static_library=true",
             "is_component_build=false",
             "v8_monolithic=true",
             "v8_use_external_startup_data=false",
             "use_custom_libcxx=false",
             "treat_warnings_as_errors=false"]

  if config.check_option("platform", "linux_arm64"):
    if os.path.exists("./customnin"):
      base.cmd("rm", ["-rf", "customnin"], False)
    if os.path.exists("./customgn"):
      base.cmd("rm", ["-rf", "customgn"], False)
    install_clang()
    gn_args.append("clang_base_path=\\\"/usr/\\\"")
    gn_args.append("clang_use_chrome_plugins=false")
    gn_args.append("use_lld = true")
    base.cmd("build/linux/sysroot_scripts/install-sysroot.py", ["--arch=arm64"], False)
    if not base.is_file("/bin/ninja"):
      base.cmd("git", ["clone", "https://github.com/ninja-build/ninja.git", "-b", "v1.8.2", "customnin"], False)
      os.chdir("customnin")
      base.cmd("./configure.py", ["--bootstrap"])
      os.chdir("../")
      base.cmd("sudo", ["cp", "-v", "customnin/ninja", "/bin/ninja"])
      shutil.rmtree("customnin")
    if os.path.exists("/core/Common/3dParty/v8_89/depot_tools/ninja"):
      base.cmd("rm", ["-v", "/core/Common/3dParty/v8_89/depot_tools/ninja"])

    base.cmd("git", ["clone", "https://gn.googlesource.com/gn", "customgn"], False)
    os.chdir("customgn")
    base.cmd("git", ["checkout", "23d22bcaa71666e872a31fd3ec363727f305417e"], False)
    base.cmd("sed", ["-i", "-e", "\"s/-Wl,--icf=all//\"", "build/gen.py"], False)
    base.cmd("python", ["build/gen.py"], False)
    base.cmd("ninja", ["-C", "out"])
    os.chdir("../")
    base.cmd("sudo", ["cp","./customgn/out/gn", "./buildtools/linux64/gn"])
    shutil.rmtree("customgn")

    base.cmd2("gn", ["gen", "out.gn/linux_arm64", make_args(gn_args, "linux", False)])
    base.cmd("ninja", ["-C", "out.gn/linux_arm64"])
  elif config.check_option("platform", "linux_64"):
    base.cmd2("gn", ["gen", "out.gn/linux_64", make_args(gn_args, "linux")])
    base.cmd("ninja", ["-C", "out.gn/linux_64"])
  elif config.check_option("platform", "linux_32"):
    base.cmd2("gn", ["gen", "out.gn/linux_32", make_args(gn_args, "linux", False)])
    base.cmd("ninja", ["-C", "out.gn/linux_32"])
  elif config.check_option("platform", "mac_64"):
    base.cmd2("gn", ["gen", "out.gn/mac_64", make_args(gn_args, "mac")])
    base.cmd("ninja", ["-C", "out.gn/mac_64"])
  elif config.check_option("platform", "win_64"):
    if (-1 != config.option("config").lower().find("debug")):
      if not base.is_file("out.gn/win_64/debug/obj/v8_monolith.lib"):
        patch_windows_debug()
        ninja_windows_make(gn_args, True, True)
        unpatch_windows_debug()

    if not base.is_file("out.gn/win_64/release/obj/v8_monolith.lib"):
      ninja_windows_make(gn_args)

  elif config.check_option("platform", "win_32"):
    if (-1 != config.option("config").lower().find("debug")):
      if not base.is_file("out.gn/win_32/debug/obj/v8_monolith.lib"):
        patch_windows_debug()
        ninja_windows_make(gn_args, False, True)
        unpatch_windows_debug()

    if not base.is_file("out.gn/win_32/release/obj/v8_monolith.lib"):
      ninja_windows_make(gn_args, False)

  os.chdir(old_cur)
  os.environ.clear()
  os.environ.update(old_env)
