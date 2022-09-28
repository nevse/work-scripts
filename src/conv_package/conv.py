#!/usr/bin/env python3
import os
import glob
import argparse
from conv_package.package import *
from conv_package.project import *

def main():
    parser = argparse.ArgumentParser(description="Convert package reference to dll reference.")
    parser.add_argument("-w", "--workpath", dest="repo_path", default="~/work/native-mobile")
    parser.add_argument("--reverse", dest="reverse", action="store_true", help="Convert dll reference to package reference.")
    parser.add_argument("--version", dest="version", default="22.2.1")
    args = parser.parse_args()

    repo_path = args.repo_path
    convert_to_package_references = args.reverse
    version = args.version

    solution_dir = os.getcwd()
    builder = PackageInfoBuilder(f"{os.path.expanduser(repo_path)}/nuspec", f"{os.path.expanduser(repo_path)}/scripts/nuget")
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
            if maui_project.has_maui_android_platform():
                maui_project.add_references(android_references, repo_path=repo_path, platform="android")
                maui_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.6.20.1", "android")
                grid_project_path = f"{repo_path}/xamarin/Maui/DevExpress.Maui.DataGrid/DevExpress.Maui.DataGrid.csproj"
                if os.path.exists(grid_project_path):                    
                    data_grid_project = ProjectInfo(grid_project_path)
                    data_package_info = data_grid_project.find_package_reference("DevExpress.Data")
                    if data_package_info != None:
                        (_, data_package_version) = data_package_info
                        maui_project.add_package_reference("DevExpress.Data", data_package_version)
            if maui_project.has_maui_ios_platform():
                maui_project.add_references(ios_references, repo_path=repo_path, platform="ios")
            maui_project.remove_package_references(packages_to_remove)
        maui_project.save()


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