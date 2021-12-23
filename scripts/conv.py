#!/usr/bin/env python3

import lxml
import lxml.etree
import os
import glob
import argparse
from collections.abc import Mapping

from lxml.etree import XMLParser

def main():
    self_check()

    parser = argparse.ArgumentParser(description="Convert package reference to dll reference.")
    parser.add_argument("--workpath", dest="repo_path", default="~/work/native-mobile")
    args = parser.parse_args()

    repo_path = args.repo_path
    solution_dir = os.getcwd()

    proj_files = glob.glob(f"{solution_dir}/**/*.csproj", recursive=True)
    (xamarin_project, android_project, ios_project, maui_project) = sortout_projects(proj_files)
    
    if (xamarin_project != None):
        packages = xamarin_project.get_package_references()

        #patch common project
        print(f"Process xamarin common project {xamarin_project.proj_file_path}")
        (refs, packages_to_remove) = find_references_to_process(packages, "common")
        xamarin_project.add_references(refs, repo_path)
        xamarin_project.remove_package_references(packages_to_remove)
        xamarin_project.save()

        #patch android project
        if (android_project != None):
            print(f"Process android project {xamarin_project.proj_file_path}")
            (refs, packages_to_remove) = find_references_to_process(packages, "android")
            android_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.5.31.2")
            android_project.add_references(refs, repo_path)
            android_project.save()

        #patch ios project
        if (ios_project != None):
            print(f"Process ios project {xamarin_project.proj_file_path}")
            (refs, packages_to_remove) = find_references_to_process(packages, "ios")
            ios_project.add_references(refs, repo_path)
            ios_project.save()
    
    if (maui_project != None):
        print("Process maui project")
        packages = maui_project.get_package_references()
        (android_references, ios_references, packages_to_remove) = find_maui_references_to_process(packages)
        if maui_project.has_maui_android_platform():
            maui_project.add_references(android_references, repo_path=repo_path, platform="android")
            maui_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.4.32.1", "android")
        if maui_project.has_maui_ios_platform():
            maui_project.add_references(ios_references, repo_path=repo_path, platform="ios")        
        maui_project.remove_package_references(packages_to_remove)
        maui_project.save()


maui_hint_path_info={
    "DevExpress.Maui.Core":{
        "android":"xamarin\Binaries\Android\DevExpress.Maui.Core.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.Core.dll"
    },
    "DevExpress.Maui.CollectionView":{
        "android":"xamarin\Binaries\Android\DevExpress.Maui.CollectionView.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.CollectionView.dll"            
    },
    "DevExpress.Xamarin.Android.CollectionView":"xamarin\Binaries\DevExpress.Xamarin.Android.CollectionView.dll",
    "DevExpress.Xamarin.iOS.CollectionView":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Xamarin.iOS.CollectionView.dll",
    "DevExpress.Maui.Editors":{
        "android":"xamarin\Binaries\Android\DevExpress.Maui.Editors.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.Editors.dll"
    },
    "DevExpress.Xamarin.Android.Editors":"xamarin\Binaries\Android\DevExpress.Xamarin.Android.Editors.dll",
    "DevExpress.Maui.iOS.Editors":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.iOS.Editors.dll",
    "DevExpress.Maui.DataGrid":{
        "android":"xamarin\Binaries\Android\DevExpress.Maui.DataGrid.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.DataGrid.dll"
    },
    "DevExpress.Xamarin.Android.Grid":"xamarin\Binaries\DevExpress.Xamarin.Android.Grid.dll",
    "DevExpress.Maui.iOS.Grid":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.iOS.Grid.dll",
    "DevExpress.Maui.Navigation":{
        "android":"xamarin\Binaries\Android\DevExpress.Maui.Navigation.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.Navigation.dll"
    },
    "DevExpress.Xamarin.Android.Navigation":"xamarin\Binaries\DevExpress.Xamarin.Android.Navigation.dll",
    "DevExpress.Maui.iOS.Navigation":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.iOS.Navigation.dll",
    "DevExpress.Maui.Charts":{
         "android":"xamarin\Binaries\Android\DevExpress.Maui.Charts.dll",
        "ios":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Maui.Charts.dll"
    },
    "DevExpress.Maui.Android.Charts":"xamarin\Binaries\Android\DevExpress.Xamarin.Android.Charts.dll",
    "DevExpress.Xamarin.iOS.Charts":"xamarin\Binaries\iOS\iossimulator-x64\DevExpress.Xamarin.iOS.Charts.dll"
}

maui_packages_info={
    "DevExpress.Maui.Core":{
        "common":[
            "DevExpress.Maui.Core"
        ],
        "android":[ ],
        "ios":[ ]
    },
    "DevExpress.Maui.CollectionView":{ 
        "common":[
            "DevExpress.Maui.Core",
            "DevExpress.Maui.CollectionView"
        ],
        "android":[ 
            "DevExpress.Xamarin.Android.CollectionView"
        ],
        "ios":[ 
            "DevExpress.Xamarin.iOS.CollectionView"
        ]
    },
    "DevExpress.Maui.Editors": {
        "common":[
            "DevExpress.Maui.Core",
            "DevExpress.Maui.CollectionView",
            "DevExpress.Maui.Editors"
        ],
        "android":[ 
            "DevExpress.Xamarin.Android.CollectionView",
            "DevExpress.Xamarin.Android.Editors"
        ],
        "ios":[ 
            "DevExpress.Xamarin.iOS.CollectionView",
            "DevExpress.Maui.iOS.Editors"
        ]
    },
    "DevExpress.Maui.DataGrid":{
        "common":[
            "DevExpress.Maui.Core",
            "DevExpress.Maui.CollectionView",
            "DevExpress.Maui.Editors",
            "DevExpress.Maui.DataGrid",
        ],
        "android":[ 
            "DevExpress.Xamarin.Android.CollectionView",
            "DevExpress.Xamarin.Android.Editors",
            "DevExpress.Xamarin.Android.Grid"
        ],
        "ios":[ 
            "DevExpress.Xamarin.iOS.CollectionView",
            "DevExpress.Maui.iOS.Editors",
            "DevExpress.Maui.iOS.Grid"
        ]
    },
    "DevExpress.Maui.Navigation":{
        "common":[
            "DevExpress.Maui.Core",
            "DevExpress.Maui.Navigation"
        ],
        "android":[
            "DevExpress.Xamarin.Android.Navigation"
        ],
        "ios":[
            "DevExpress.Maui.iOS.Navigation"
        ]
    },
    "DevExpress.Maui.Charts":{
        "common":[
            "DevExpress.Maui.Core",
            "DevExpress.Maui.Charts"
        ],
        "android":[
            "DevExpress.Maui.Android.Charts"
         ],
        "ios":[
            "DevExpress.Xamarin.iOS.Charts"
         ]
    }
}

xamarin_packages_info={
    "DevExpress.XamarinForms.Core":{
        "common":[
            "DevExpress.XamarinForms.Core"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS"
        ]
    },
    "DevExpress.XamarinForms.Charts":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.Charts"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.Charts",
            "DevExpress.XamarinForms.Charts.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.Xamarin.iOS.Charts",
            "DevExpress.XamarinForms.Charts.iOS"
        ]
    },
    "DevExpress.XamarinForms.CollectionView":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.CollectionView"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.CollectionView",
            "DevExpress.XamarinForms.CollectionView.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.Xamarin.iOS.CollectionView",
            "DevExpress.XamarinForms.CollectionView.iOS"
        ]
    },
    "DevExpress.XamarinForms.Scheduler":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.Scheduler"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.Scheduler",
            "DevExpress.XamarinForms.Scheduler.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.Xamarin.iOS.Scheduler",
            "DevExpress.XamarinForms.Scheduler.iOS"
        ]
    },
    "DevExpress.XamarinForms.Grid":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.Grid",
            "DevExpress.XamarinForms.Editors",
            "DevExpress.XamarinForms.CollectionView"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.Grid",
            "DevExpress.XamarinForms.Grid.Android",
            "DevExpress.Xamarin.Android.Editors",
            "DevExpress.XamarinForms.Editors.Android",
            "DevExpress.Xamarin.Android.CollectionView",
            "DevExpress.XamarinForms.CollectionView.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.Xamarin.iOS.Grid",
            "DevExpress.XamarinForms.Editors.iOS",
            "DevExpress.Xamarin.iOS.Editors",
            "DevExpress.Xamarin.iOS.CollectionView",
            "DevExpress.XamarinForms.CollectionView.iOS"
        ]
    },
    "DevExpress.XamarinForms.Navigation":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.Navigation"
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.Navigation",
            "DevExpress.XamarinForms.Navigation.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.Xamarin.iOS.Navigation",
            "DevExpress.XamarinForms.Navigation.iOS"
        ]
    },    
    "DevExpress.XamarinForms.Editors":{
        "common":[
            "DevExpress.XamarinForms.Core",
            "DevExpress.XamarinForms.Editors",
            "DevExpress.XamarinForms.CollectionView",
        ],
        "android":[
            "DevExpress.XamarinForms.Core.Android",
            "DevExpress.Xamarin.Android.Editors",
            "DevExpress.XamarinForms.Editors.Android",
            "DevExpress.Xamarin.Android.CollectionView",
            "DevExpress.XamarinForms.CollectionView.Android"
        ],
        "ios":[
            "DevExpress.XamarinForms.Core.iOS",
            "DevExpress.XamarinForms.Editors.iOS",
            "DevExpress.Xamarin.iOS.Editors",
            "DevExpress.Xamarin.iOS.CollectionView",
            "DevExpress.XamarinForms.CollectionView.iOS"
        ]
    }
}



hint_path_info={
    "DevExpress.XamarinForms.Core":"xamarin\Binaries\DevExpress.XamarinForms.Core.dll",
    "DevExpress.XamarinForms.Editors":"xamarin\Binaries\DevExpress.XamarinForms.Editors.dll",
    "DevExpress.XamarinForms.CollectionView":"xamarin\Binaries\DevExpress.XamarinForms.CollectionView.dll",
    "DevExpress.Xamarin.Android.Editors":"xamarin\Binaries\DevExpress.Xamarin.Android.Editors.dll",
    "DevExpress.XamarinForms.Editors.Android":"xamarin\Binaries\DevExpress.XamarinForms.Editors.Android.dll",
    "DevExpress.Xamarin.Android.CollectionView":"xamarin\Binaries\DevExpress.Xamarin.Android.CollectionView.dll",
    "DevExpress.XamarinForms.CollectionView.Android":"xamarin\Binaries\DevExpress.XamarinForms.CollectionView.Android.dll",
    "DevExpress.XamarinForms.CollectionView.iOS":"xamarin\Binaries\DevExpress.XamarinForms.CollectionView.iOS.dll",
    "DevExpress.XamarinForms.Editors.iOS":"xamarin\Binaries\DevExpress.XamarinForms.Editors.iOS.dll",
    "DevExpress.Xamarin.iOS.Editors":"xamarin\Binaries\DevExpress.Xamarin.iOS.Editors.dll",
    "DevExpress.Xamarin.iOS.CollectionView":"xamarin\Binaries\DevExpress.Xamarin.iOS.CollectionView.dll",
    "DevExpress.XamarinForms.Core.Android":"xamarin\Binaries\DevExpress.XamarinForms.Core.Android.dll",
    "DevExpress.XamarinForms.Core.iOS":"xamarin\Binaries\DevExpress.XamarinForms.Core.iOS.dll",
    "DevExpress.XamarinForms.Charts":"xamarin\Binaries\DevExpress.XamarinForms.Charts.dll",
    "DevExpress.Xamarin.Android.Charts":"xamarin\Binaries\DevExpress.Xamarin.Android.Charts.dll",
    "DevExpress.XamarinForms.Charts.Android":"xamarin\Binaries\DevExpress.XamarinForms.Charts.Android.dll",
    "DevExpress.Xamarin.iOS.Charts":"xamarin\Binaries\DevExpress.Xamarin.iOS.Charts.dll",
    "DevExpress.XamarinForms.Charts.iOS":"xamarin\Binaries\DevExpress.XamarinForms.Charts.iOS.dll",
    "DevExpress.XamarinForms.Scheduler":"xamarin\Binaries\DevExpress.XamarinForms.Scheduler.dll",
    "DevExpress.Xamarin.Android.Scheduler":"xamarin\Binaries\DevExpress.Xamarin.Android.Scheduler.dll",
    "DevExpress.XamarinForms.Scheduler.Android":"xamarin\Binaries\DevExpress.XamarinForms.Scheduler.Android.dll",
    "DevExpress.Xamarin.iOS.Scheduler":"xamarin\Binaries\DevExpress.Xamarin.iOS.Scheduler.dll",
    "DevExpress.XamarinForms.Scheduler.iOS":"xamarin\Binaries\DevExpress.XamarinForms.Scheduler.iOS.dll",
    "DevExpress.XamarinForms.Grid":"xamarin\Binaries\DevExpress.XamarinForms.Grid.dll",
    "DevExpress.Xamarin.Android.Grid":"xamarin\Binaries\DevExpress.Xamarin.Android.Grid.dll",
    "DevExpress.XamarinForms.Grid.Android":"xamarin\Binaries\DevExpress.XamarinForms.Grid.Android.dll",
    "DevExpress.Xamarin.iOS.Grid":"xamarin\Binaries\DevExpress.Xamarin.iOS.Grid.dll",
    "DevExpress.XamarinForms.Navigation":"xamarin\Binaries\DevExpress.XamarinForms.Navigation.dll",
    "DevExpress.Xamarin.Android.Navigation":"xamarin\Binaries\DevExpress.Xamarin.Android.Navigation.dll",
    "DevExpress.XamarinForms.Navigation.Android":"xamarin\Binaries\DevExpress.XamarinForms.Navigation.Android.dll",
    "DevExpress.Xamarin.iOS.Navigation":"xamarin\Binaries\DevExpress.Xamarin.iOS.Navigation.dll",
    "DevExpress.XamarinForms.Navigation.iOS":"xamarin\Binaries\DevExpress.XamarinForms.Navigation.iOS.dll",
}

def self_check():
    reference_set = set()
    for package in xamarin_packages_info:
        package_info = xamarin_packages_info[package]
        for platform in package_info:
            for reference in package_info[platform]:
                if reference in reference_set:
                    continue
                reference_set.add(reference)
                if hint_path_info.get(reference) == None:
                    print(f"Can't find path for reference {reference}")

    for package in maui_packages_info:
        package_info = maui_packages_info[package]
        for platform in package_info:
            for reference in package_info[platform]:
                reference_info = maui_hint_path_info.get(reference)
                if reference_info == None:
                    print(f"Can't find path for reference {reference}")
                    continue
                if isinstance(reference_info, Mapping):
                    if reference_info.get("android") == None and reference_info.get("ios") == None:
                        print(f"Can't find path for reference {reference}")

class ProjectInfo:
    msbuild_namespaces = {"ns":"http://schemas.microsoft.com/developer/msbuild/2003"}

    def __init__(self, proj_file_path):
        self.proj_file_path = proj_file_path
        parser = XMLParser(remove_blank_text=True)
        self.document = lxml.etree.parse(proj_file_path, parser)
        self.root = self.document.getroot()
        self.use_namespace = len(self.root.nsmap) > 0

    def set_hint_path_info(self, hint_path_info):
        self.hint_path_info = hint_path_info

    def save(self):
        indx = 0
        backup_path = f"{self.proj_file_path}.bak"
        while(os.path.exists(backup_path)):            
            indx += 1
            backup_path = f"{self.proj_file_path}.bak{indx}"
        os.rename(self.proj_file_path, backup_path)
        self.document.write(self.proj_file_path, pretty_print=True, encoding="utf-8")

    def has_maui_android_platform(self):
        nodes = self.document.xpath("//PropertyGroup//TargetFrameworks")
        return len(nodes) == 1 and "net6.0-android" in nodes[0].text.lower()
    
    def has_maui_ios_platform(self):
        nodes = self.document.xpath("//PropertyGroup//TargetFrameworks")
        return len(nodes) == 1 and "net6.0-ios" in nodes[0].text.lower()

    def is_android(self):
        nodes = self.document.xpath("//ns:Import[contains(@Project, 'Xamarin.Android.CSharp.targets')]", namespaces=self.msbuild_namespaces)
        return len(nodes) > 0
    
    def is_ios(self):
        nodes = self.document.xpath("//ns:Import[contains(@Project, 'Xamarin.iOS.CSharp.targets')]", namespaces=self.msbuild_namespaces)
        return len(nodes) > 0

    def is_xamarin(self):
        nodes = self.document.xpath("//PropertyGroup//TargetFramework")
        return len(nodes) == 1 and nodes[0].text == "netstandard2.0"

    def is_maui(self):
        nodes = self.document.xpath("//PropertyGroup//UseMaui")
        return len(nodes) == 1 and nodes[0].text.lower() == "true"

    def get_package_references(self):
        packages = []
        package_ref_nodes = self.get_packagereference_nodes()
        for item in package_ref_nodes:
            packages.append(item.get("Include"))
        return packages

    def add_package_reference(self, package, version, platform=""):
        packages = self.get_package_references()
        if package in packages:
            print(f"Skip add package {package}, reason - already exist")
            return
        package_ref_nodes = self.get_packagereference_nodes()
        condition = f"'$(TargetFramework)' == 'net6.0-{platform}'"
        content_node = None
        if len(package_ref_nodes) != 0:
            if platform == "":
                content_node = package_ref_nodes[0].getparent()
            else:
                content_node = next((x.getparent() for x in package_ref_nodes if self.check_condition(x.getparent(), condition)), None)
        
        if content_node == None:
            project_node = self.get_project_node()
            content_node = lxml.etree.Element("ItemGroup")
            if (platform != ""):
                content_node.attrib["Condition"] = condition
            project_node.append(content_node)
                        
        package_node = lxml.etree.Element("PackageReference")
        content_node.append(package_node)
        package_node.attrib["Include"] = package
        version_node = lxml.etree.SubElement(package_node, "Version")
        version_node.text = version
        print(f"Add package {package}")

    def check_condition(self, element, condition):
        condition_attr = element.attrib.get("Condition")
        if condition_attr == None:
            return False
        return condition_attr.replace(" ", "") == condition.replace(" ", "")

    def add_references(self, references, repo_path, platform=""):
        package_ref_nodes = self.get_packagereference_nodes()
        condition = None
        if platform != "":
            condition = f"'$(TargetFramework)' == 'net6.0-{platform}'"
            item_group_node = next((x.getparent() for x in package_ref_nodes if self.check_condition(x.getparent(), condition)), None)
        else:
            item_group_node = package_ref_nodes[0].getparent() if len(package_ref_nodes) > 0 else None
        ref_content_node = lxml.etree.Element("ItemGroup")
        if condition != None:
            ref_content_node.attrib["Condition"] = condition
        if item_group_node == None:
            project_node = self.get_project_node()
            project_node.append(ref_content_node)
        else:
            item_group_node.addnext(ref_content_node)
        for ref in references:
            hint_path = self.hint_path_info.get(ref)
            if hint_path == None:
                print(f"Can't find hint path for {ref}")
                continue
            if isinstance(hint_path, Mapping):
                hint_path = hint_path.get(platform)
                if hint_path == None or hint_path == "":
                    print(f"Can't find hint path for {ref} for platform {platform}")
                    continue                
            ref_node = lxml.etree.SubElement(ref_content_node, "Reference")
            ref_node.attrib["Include"] = ref
            hint_path_node = lxml.etree.SubElement(ref_node, "HintPath")
            ref_abs_path = os.path.join(os.path.expanduser(repo_path), hint_path)
            ref_rel_path = os.path.relpath(ref_abs_path, os.path.dirname(self.proj_file_path))
            hint_path_node.text = self.patch_path(ref_rel_path)
            print(f"Add reference {ref}")

    def remove_package_references(self, packages_to_remove):
        package_ref_nodes = self.get_packagereference_nodes()
        for element in package_ref_nodes:
            package_name = element.attrib["Include"]
            if package_name in packages_to_remove:
                parent = element.getparent()
                parent.remove(element)
                print(f"Remove package {package_name}")

    def get_packagereference_nodes(self):
        return self.document.xpath("//ns:PackageReference", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("//PackageReference")

    def get_project_node(self):
        nodes = self.document.xpath("ns:Project", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("//Project")
        return nodes[0]

    def patch_path(self, path):
        return path.replace('/', '\\')

def sortout_projects(proj_files):
    xamarin = None
    android = None
    ios = None
    maui = None
    for proj_path in proj_files:
        proj = ProjectInfo(proj_path)
        if proj.is_android():
            android = proj
            proj.set_hint_path_info(hint_path_info)
            continue

        if proj.is_ios():
            ios = proj
            proj.set_hint_path_info(hint_path_info)
            continue

        if proj.is_xamarin():
            xamarin = proj
            proj.set_hint_path_info(hint_path_info)
            continue

        if proj.is_maui():
            maui = proj
            proj.set_hint_path_info(maui_hint_path_info)
            continue

    return (xamarin, android, ios, maui)

def find_references_to_process(packages, type):
    result = set()
    packages_to_remove = set()
    for package in packages:
        package_info = xamarin_packages_info.get(package)
        refs = package_info.get(type) if package_info != None else []
        if len(refs) == 0:
            print(f"Skip package {package}")
            continue
        packages_to_remove.add(package)
        for ref in refs:
            result.add(ref)            
    return (result, packages_to_remove)

def find_maui_references_to_process(packages):
    android_references = set()
    ios_references = set()
    packages_to_remove = set()
    for package in packages:
        package_was_processed = False
        package_info = maui_packages_info.get(package)
        if package_info == None:
            print(f"Skip package {package}")
            continue
        refs = package_info.get("common")
        if len(refs) != 0:
            package_was_processed = True
            for ref in refs:
                android_references.add(ref)
                ios_references.add(ref)
        
        refs = package_info.get("android")
        if len(refs) != 0:
            package_was_processed = True
            for ref in refs:
                android_references.add(ref)

        refs = package_info.get("ios")
        if len(refs) != 0:
            package_was_processed = True
            for ref in refs:
                ios_references.add(ref)

        if package_was_processed:
            packages_to_remove.add(package)
        else:
            print(f"Skip package {package}")
        
    return (android_references, ios_references, packages_to_remove)

main()