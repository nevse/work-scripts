#!/usr/bin/env python3
import os
import glob
import argparse
from conv_package.package import *
from conv_package.project import *

def main():
    parser = argparse.ArgumentParser(description="Convert package reference to dll reference.")
    parser.add_argument("-w", "--workpath", dest="repo_path", default="~/work/native-mobile")
    parser.add_argument("-d", "--use-dll", dest="use_dll", action="store_true", help="Convert package reference to dll reference.")
    parser.add_argument("--reverse", dest="reverse", action="store_true", help="Convert dll reference to package reference.")
    parser.add_argument("--version", dest="version", default="22.2.1")
    parser.add_argument("-p", "--project-refs", dest="project_refs", action="store_true", help="Convert package reference to project reference.")
    args = parser.parse_args()

    repo_path = args.repo_path
    convert_to_package_references = args.reverse
    version = args.version
    use_dll = args.use_dll
    project_refs = args.project_refs

    solution_dir = os.getcwd()
    full_repo_path = os.path.expanduser(repo_path)
    builder = PackageInfoBuilder(full_repo_path, "nuspec", "scripts/nuget")
    packages = builder.build_packages()
    package_storage = PackageStorage(packages)
    proj_files = glob.glob(f"{solution_dir}/**/*.csproj", recursive=True)
    (xamarin_project, android_project, ios_project, maui_project) = sortout_projects(proj_files)
    
    if (xamarin_project != None):
        if convert_to_package_references:
            print("not implemented yet!")
            return 0
        package_references = xamarin_project.get_package_references()
        #patch common project
        print(f"Process xamarin common project {xamarin_project.proj_file_path}")
        (refs, packages_to_remove) = package_storage.find_common_references(package_references)
        xamarin_project.add_references(refs, repo_path)
        xamarin_project.remove_package_references(packages_to_remove)
        xamarin_project.save()

        #patch android project
        if (android_project != None):
            print(f"Process android project {android_project.proj_file_path}")
            (refs, packages_to_remove) = package_storage.find_android_references(package_references)
            android_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.5.31.2")
            android_project.add_references(refs, repo_path)
            android_project.remove_package_references(packages_to_remove)
            android_project.save()

        #patch ios project
        if (ios_project != None):
            print(f"Process ios project {ios_project.proj_file_path}")
            (refs, packages_to_remove) = package_storage.find_ios_references(package_references)
            ios_project.add_references(refs, repo_path)
            ios_project.remove_package_references(packages_to_remove)   
            ios_project.save()

    if (maui_project != None):
        print("Process maui project")
        if convert_to_package_references:
            dll_references = maui_project.get_references()
            (packages_to_add, references_to_remove) = package_storage.find_maui_packages(dll_references)
            maui_project.remove_references(references_to_remove)
            maui_project.add_package_references(packages_to_add, version)
            maui_project.remove_package_references(["Xamarin.Kotlin.StdLib"])
            maui_project.clean_empty_groups()
        else:
            package_references = maui_project.get_package_references()
            
            (android_references, ios_references, packages_to_remove) = package_storage.find_maui_references_to_process(package_references)
            build_props_path = os.path.expanduser(f"{repo_path}/xamarin/Maui/Build.props")
            if os.path.exists(build_props_path):
                data_versions = find_data_version(os.path.expanduser(f"{repo_path}/xamarin/Maui"))                    
                build_props = ProjectInfo(build_props_path)
                data_package_info = build_props.find_package_reference("DevExpress.Data")
                if data_package_info != None:
                    (_, data_package_version) = data_package_info
                    data_package_version = data_versions[0] if data_versions != None else data_package_version
                    maui_project.add_package_reference("DevExpress.Data", data_package_version)
            if not use_dll:
                common_references = set()
                android_references_to_remove = set()
                ios_references_to_remove = set()
                for android_ref in android_references:
                    for ios_ref in ios_references:
                        if android_ref.project_path == ios_ref.project_path:
                            common_references.add(android_ref)
                            android_references_to_remove.add(android_ref)
                            ios_references_to_remove.add(ios_ref)
                for ref in android_references_to_remove:
                    android_references.remove(ref)
                for ref in ios_references_to_remove:
                    ios_references.remove(ref)
            if not use_dll and project_refs:
                replace_for_project_refs_suffix(android_references)
                replace_for_project_refs_suffix(ios_references)
                replace_for_project_refs_suffix(common_references)
            if not use_dll:
                maui_project.add_references(common_references, repo_path=repo_path, platform="", use_dll=False)
            if maui_project.has_maui_android_platform():
                maui_project.add_references(android_references, repo_path=repo_path, platform="android", use_dll=use_dll)
                #maui_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.6.20.1", "android")
            if maui_project.has_maui_ios_platform():
                maui_project.add_references(ios_references, repo_path=repo_path, platform="ios", use_dll=use_dll)
            maui_project.remove_package_references(packages_to_remove)
        maui_project.save()

def replace_for_project_refs_suffix(references):
    for ref in references:
        if ref.project_path.endswith(".csproj"):
            ref.project_path = ref.project_path[:(len(ref.project_path)-len(".csproj"))] + ".Refs.csproj"
def find_data_version(maui_path):
    data_version = None
    if not os.path.exists(maui_path):
        return data_version
    proj_files = glob.glob(f"{maui_path}/**/*.csproj", recursive=True)
    for proj_path in proj_files:
        proj = ProjectInfo(proj_path)
        data_version = proj.get_property("DevExpress_Data")
        if data_version != None:
            break
    return data_version

def sortout_projects(proj_files):
    xamarin = None
    android = None
    ios = None
    maui = None
    for proj_path in proj_files:
        proj = ProjectInfo(proj_path)
        if proj.is_android():
            android = proj
            continue

        if proj.is_ios():
            ios = proj
            continue

        if proj.is_xamarin():
            xamarin = proj
            continue

        if proj.is_maui():
            maui = proj
            continue

    return (xamarin, android, ios, maui)

if __name__ == "__main__":
    main()