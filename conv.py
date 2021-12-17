#!/usr/bin/env python3

import lxml
import lxml.etree
import os
import glob
import argparse

from lxml.etree import XMLParser

def main():
    self_check()

    parser = argparse.ArgumentParser(description="Convert package reference to dll reference.")
    parser.add_argument("--workpath", dest="repo_path", default="~/work/native-mobile")
    args = parser.parse_args()

    repo_path = args.repo_path
    solution_dir = os.getcwd()

    proj_files = glob.glob(f"{solution_dir}/**/*.csproj", recursive=True)
    (xamarin_project, android_project, ios_project) = sortout_projects(proj_files)
    packages = xamarin_project.get_package_references()

    #patch common project
    print(f"Process xamarin common project {xamarin_project.proj_file_path}")
    (refs, packages_to_remove) = find_references_to_process(packages, "common")
    xamarin_project.add_references(refs, repo_path)
    xamarin_project.remove_package_references(packages_to_remove)
    xamarin_project.save()

    #patch android project
    print(f"Process android project {xamarin_project.proj_file_path}")
    (refs, packages_to_remove) = find_references_to_process(packages, "android")
    android_project.add_package_reference("Xamarin.Kotlin.StdLib", "1.5.31.2")
    android_project.add_references(refs, repo_path)
    android_project.save()

    #patch ios project
    print(f"Process ios project {xamarin_project.proj_file_path}")
    (refs, packages_to_remove) = find_references_to_process(packages, "ios")
    ios_project.add_references(refs, repo_path)
    ios_project.save()

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

class ProjectInfo:
    msbuild_namespaces = {"ns":"http://schemas.microsoft.com/developer/msbuild/2003"}

    def __init__(self, proj_file_path):
        self.proj_file_path = proj_file_path
        parser = XMLParser(remove_blank_text=True)
        self.document = lxml.etree.parse(proj_file_path, parser)
        self.root = self.document.getroot()
        self.use_namespace = len(self.root.nsmap) > 0

    def save(self):
        self.document.write(f"{self.proj_file_path}_conv2", pretty_print=True, encoding="utf-8")

    def is_android(self):
        nodes = self.document.xpath("//ns:Import[contains(@Project, 'Xamarin.Android.CSharp.targets')]", namespaces=self.msbuild_namespaces)
        return len(nodes) > 0
    
    def is_ios(self):
        nodes = self.document.xpath("//ns:Import[contains(@Project, 'Xamarin.iOS.CSharp.targets')]", namespaces=self.msbuild_namespaces)
        return len(nodes) > 0

    def is_xamarin(self):
        nodes= self.document.xpath("//PropertyGroup//TargetFramework")
        return len(nodes) == 1 and nodes[0].text == "netstandard2.0"

    def get_package_references(self):
        packages = []
        package_ref_nodes = self.get_packagereference_nodes()
        for item in package_ref_nodes:
            packages.append(item.get("Include"))
        return packages

    def add_package_reference(self, package, version):
        packages = self.get_package_references()
        if package in packages:
            print(f"Skip add package {package}, reason - already exist")
            return
        package_ref_nodes = self.get_packagereference_nodes()
        content_node = None
        if len(package_ref_nodes) == 0:
            project_node = self.get_project_node()
            content_node = lxml.etree.Element("ItemGroup")
            project_node.add(content_node)
        else:
            content_node = package_ref_nodes[0].getparent()
        package_node = lxml.etree.Element("PackageReference")
        content_node.append(package_node)
        package_node.attrib["Include"] = package
        version_node = lxml.etree.SubElement(package_node, "HintPath")
        version_node.text = version
        print(f"Add package {package}")

    def add_references(self, references, repo_path):
        package_ref_nodes = self.get_packagereference_nodes()
        item_group_node = package_ref_nodes[0].getparent() if len(package_ref_nodes) > 0 else None
        ref_content_node = lxml.etree.Element("ItemGroup")
        if item_group_node == None:
            project_node = self.get_project_node()
            project_node.add(ref_content_node)
        else:
            item_group_node.addnext(ref_content_node)
        for ref in references:
            hint_path = hint_path_info.get(ref)
            if hint_path == None:
                print(f"Can't find hint path for {ref}")
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
        nodes = self.document.xpath("ns:Project", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("Project")
        return nodes[0]

    def patch_path(self, path):
        return path.replace('/', '\\')

def sortout_projects(proj_files):
    xamarin = None
    android = None
    ios = None
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

    return (xamarin, android, ios)

def find_references_to_process(packages, type):
    result = set()
    packages_to_remove = set()
    for package in packages:
        package_info = xamarin_packages_info.get(package)
        refs=package_info.get(type) if package_info != None else []
        if len(refs) == 0:
            print(f"Skip package {package}")
            continue
        packages_to_remove.add(package)
        for ref in refs:
            result.add(ref)            
    return (result, packages_to_remove)

main()