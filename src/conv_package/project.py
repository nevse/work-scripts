import lxml
import lxml.etree
import os
from conv_package.package import *
from lxml.etree import XMLParser

class ProjectInfo:
    msbuild_namespaces = {"ns":"http://schemas.microsoft.com/developer/msbuild/2003"}

    def __init__(self, proj_file_path):
        self.proj_file_path = proj_file_path
        parser = XMLParser(remove_blank_text=True)
        self.document = lxml.etree.parse(proj_file_path, parser)
        self.root = self.document.getroot()
        self.use_namespace = len(self.root.nsmap) > 0

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
        for node in nodes:
            if "net6.0-android" in node.text.lower():
                return True
        return False
    
    def has_maui_ios_platform(self):
        nodes = self.document.xpath("//PropertyGroup//TargetFrameworks")
        for node in nodes:
            if "net6.0-ios" in node.text.lower():
                return True
        return False

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
            hint_path = ref.path
            if hint_path == None:
                print(f"Can't find hint path for {ref}")
                continue
            ref_node = lxml.etree.SubElement(ref_content_node, "Reference")
            ref_node.attrib["Include"] = ref.reference
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