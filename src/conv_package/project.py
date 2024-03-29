import lxml
import lxml.etree
import os
import re
from conv_package.package import *
from lxml.etree import XMLParser
from pathlib import Path

class ProjectInfo:
    msbuild_namespaces = {"ns":"http://schemas.microsoft.com/developer/msbuild/2003"}

    def __init__(self, proj_file_path):
        self.proj_file_path = proj_file_path
        parser = XMLParser(remove_blank_text=True)
        self.document = lxml.etree.parse(proj_file_path, parser)
        self.build_props_documents = self.get_build_props(proj_file_path, parser)
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

    def get_build_props(self, proj_file_path, parser: XMLParser):
        build_props = []
        proj_dir = os.path.dirname(proj_file_path)
        path = Path(proj_dir)
        build_props_file_name = os.path.join(path.parent.absolute(), "Directory.Build.props")
        if not os.path.exists(build_props_file_name):
            return build_props
        build_props.append(lxml.etree.parse(build_props_file_name, parser))
        return build_props

    def has_maui_android_platform(self):
        nodes = self.search_nodes("//PropertyGroup//TargetFrameworks")
        for node in nodes:
            if "android" in node.text.lower():
                return True
        return False
    
    def has_maui_ios_platform(self):
        nodes = self.search_nodes("//PropertyGroup//TargetFrameworks")
        for node in nodes:
            if "ios" in node.text.lower():
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
        nodes = self.search_nodes("//PropertyGroup//UseMaui")
        return len(nodes) == 1 and nodes[0].text.lower() == "true"

    def search_nodes(self, path):
        result = []
        nodes = self.document.xpath(path)
        result.extend(nodes)
        for build_props_document in self.build_props_documents:
            nodes = build_props_document.xpath(path)
            result.extend(nodes)
        return result

    def get_package_references(self):
        packages = []
        package_ref_nodes = self.get_packagereference_nodes()
        for item in package_ref_nodes:
            packages.append(item.get("Include"))
        return packages

    def find_package_reference(self, package_name):
        documents = [self.document] + self.build_props_documents
        for document in documents:
            package_ref_nodes = self.get_document_packagereference_nodes(document)
            for element in package_ref_nodes:
                if element.attrib["Include"] == package_name:
                    return (package_name, element.attrib.get("Version"))
        return None
        

    def get_references(self):
        references = dict()
        reference_nodes = self.get_reference_nodes()
        for item in reference_nodes:
            group_node = item.getparent()
            condition = group_node.get("Condition")
            platform = None
            if condition != None:
                if condition.lower().find("android") != -1:
                    platform = "android"
                if condition.lower().find("ios") != -1:
                    platform = "ios"
            if platform not in references:
                references[platform] = []
            references[platform].append(item.get("Include"))
        return references

    def add_package_references(self, packages_to_add, version, platform=""):
        for package in packages_to_add:
            self.add_package_reference(package, version, platform)

    def add_package_reference(self, package, version, platform=""):
        packages = self.get_package_references()
        if package in packages:
            print(f"Skip add package {package}, reason - already exist")
            return
        package_ref_nodes = self.get_packagereference_nodes()
        condition = platform
        content_node = None
        if len(package_ref_nodes) != 0:
            if platform == "":                
                content_node = next((x.getparent() for x in package_ref_nodes if self.is_no_condition(x.getparent(), condition)), None)
            else:
                content_node = next((x.getparent() for x in package_ref_nodes if self.check_condition(x.getparent(), condition)), None)
        
        if content_node == None:
            project_node = self.get_project_node()
            content_node = lxml.etree.Element("ItemGroup")
            if (platform != ""):
                content_node.attrib["Condition"] = f"$(TargetFramework.Contains('-{condition}'))"
            project_node.append(content_node)
                        
        package_node = lxml.etree.Element("PackageReference")
        content_node.append(package_node)
        package_node.attrib["Include"] = package
        package_node.attrib["Version"] = version        
        print(f"Add package {package}")

    def is_no_condition(self, elemnt, condition):
        condition_attr = elemnt.attrib.get("Condition")
        return condition_attr == None

    def check_condition(self, element, condition):
        condition_attr = element.attrib.get("Condition")
        if condition_attr == None:
            return False
        return condition_attr.replace(" ", "") == condition.replace(" ", "")

    def add_references(self, references, repo_path, platform="", use_dll=False):
        package_ref_nodes = self.get_packagereference_nodes()
        condition = None
        if platform != "":
            condition = platform
            item_group_node = next((x.getparent() for x in package_ref_nodes if self.check_condition(x.getparent(), condition)), None)
        else:
            item_group_node = package_ref_nodes[0].getparent() if len(package_ref_nodes) > 0 else None
        ref_content_node = lxml.etree.Element("ItemGroup")
        if condition != None:
            ref_content_node.attrib["Condition"] = f"$(TargetFramework.Contains('-{condition}'))"
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
            ref_node = lxml.etree.SubElement(ref_content_node, "Reference" if use_dll else "ProjectReference")
            if use_dll:
                ref_node.attrib["Include"] = ref.reference
                hint_path_node = lxml.etree.SubElement(ref_node, "HintPath")
                ref_abs_path = os.path.join(os.path.expanduser(repo_path), hint_path)
                ref_rel_path = os.path.relpath(ref_abs_path, os.path.dirname(self.proj_file_path))
                hint_path_node.text = self.patch_path(ref_rel_path)
                print(f"Add reference {ref.reference}")
            else:
                ref_node.attrib["Include"] = ref.project_path
                print(f"Add project reference {ref.reference} - {ref.project_path}")

    def remove_package_references(self, packages_to_remove):
        package_ref_nodes = self.get_packagereference_nodes()
        for element in package_ref_nodes:
            package_name = element.attrib["Include"]
            if package_name in packages_to_remove:
                parent = element.getparent()
                parent.remove(element)
                print(f"Remove package {package_name}")

    def clean_empty_groups(self):
        item_groups = self.get_group_nodes()
        for item_group in item_groups:
            if len(item_group.getchildren()) == 0:
                parent = item_group.getparent()
                parent.remove(item_group)

    def remove_references(self, references_to_remove):
        reference_nodes = self.get_reference_nodes()
        for element in reference_nodes:
            reference_name = element.attrib["Include"]
            group_node = element.getparent()
            condition = group_node.get("Condition")
            if "devexpress" not in reference_name.lower():
                continue
            for platform in references_to_remove:
                if platform not in condition.lower():
                    continue
                references = references_to_remove[platform]
                if reference_name in references:
                    group_node.remove(element)
                    print(f"Remove reference {reference_name}")

    def get_property(self, property_name):
        return self.get_property_matches(self.proj_file_path, property_name)

    def get_property_matches(self, project_path, property_name, is_end_point=False):
        if not os.path.exists(project_path):
            return None

        with open(project_path, 'r') as f:
            content = f.read()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

        # Find in current project
        property_match = re.findall(fr'<{property_name}\s?.*>(.*?)<\/{property_name}>\s*\n', content)
        if len(property_match) > 0:
            return property_match

        import_regex = re.compile(r'<Import\s+Project\s*=\s*"(.+?)"')
        # Find in imported project
        for import_match in import_regex.finditer(content):
            base_path = os.path.dirname(project_path)
            imported_project_name = import_match.group(1).replace('$(MSBuildThisFileDirectory)', '')
            imported_project_path = os.path.join(base_path, imported_project_name).replace('\\', '/')

            if not os.path.exists(imported_project_path):
                imported_project_path = import_match.group(1).replace('\\', '/')
            if not os.path.exists(imported_project_path):
                return None

            imported_project_property_matches = self.get_property_matches(imported_project_path, property_name, is_end_point)
            if imported_project_property_matches is not None:
                return imported_project_property_matches

        # Already at the end of the import chain
        if is_end_point:
            return None

        # Find in Directory.Build.props
        props_file = self.get_directory_props_path(os.path.dirname(project_path))
        if props_file is None:
            return None

        return self.get_property_matches(props_file, property_name, True)
    
    def get_directory_props_path(self, workspace_path):
        prop_files = [f for f in os.listdir(workspace_path) if f == 'Directory.Build.props']
        if len(prop_files) > 0:
            return os.path.join(workspace_path, prop_files[0])

        parent_directory = os.path.dirname(workspace_path)
        if parent_directory == workspace_path:
            return None
        return self.get_directory_props_path(parent_directory)
    
    def get_packagereference_nodes(self):
        return self.get_document_packagereference_nodes(self.document)

    def get_document_packagereference_nodes(self, document):
        return document.xpath("//ns:PackageReference", namespaces=self.msbuild_namespaces) if self.use_namespace else document.xpath("//PackageReference")

    def get_group_nodes(self):
        return self.document.xpath("//ns:ItemGroup", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("//ItemGroup")

    def get_reference_nodes(self):
        return self.document.xpath("//ns:Reference", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("//Reference")

    def get_project_node(self):
        nodes = self.document.xpath("ns:Project", namespaces=self.msbuild_namespaces) if self.use_namespace else self.document.xpath("//Project")
        return nodes[0]

    def patch_path(self, path):
        return path.replace('/', '\\')