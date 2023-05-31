
import lxml
import lxml.etree
import glob
import json
import os

from lxml.etree import XMLParser
class MauiPackageInfo:
    def __init__(self, id):
        self.id = id
        self.dependencies = []
        self.android_dependencies = []
        self.android_project_references = dict()
        self.ios_dependencies = []
        self.ios_references = dict()
        self.ios_project_references = dict()
        self.android_references = dict()
        self.references = dict()
        

    def is_maui(self):
        return ".maui." in self.id.lower()

    def add_android_project_reference(self, android_reference, local_package_path):
        self.android_project_references[android_reference] = local_package_path

    def add_ios_project_reference(self, ios_reference, local_package_path):
        self.ios_project_references[ios_reference] = local_package_path


    def make_all_reference_paths_absolute(self, root_path):
        for reference in self.references:
            if not os.path.isabs(self.references[reference]):
                self.references[reference] = self.get_absolute_path(root_path, self.references[reference])
        for reference in self.ios_references:
            if not os.path.isabs(self.ios_references[reference]):
                self.ios_references[reference] = self.get_absolute_path(root_path, self.ios_references[reference])
        for reference in self.android_references:
            if not os.path.isabs(self.android_references[reference]):
                self.android_references[reference] = self.get_absolute_path(root_path, self.android_references[reference])
    
    def get_absolute_path(self, root_path, path):
        if os.path.isabs(path):
            return path;
        joined_path = os.path.join(root_path, path)
        return os.path.abspath(joined_path)

    def add_dependency(self, dependency):
        self.dependencies.append(dependency)

    def add_android_dependency(self, android_dependency):
        self.android_dependencies.append(android_dependency)
    
    def add_ios_dependency(self, ios_dependency):
        self.ios_dependencies.append(ios_dependency)

    def add_reference(self, common_reference, local_package_path):
        self.references[common_reference] = local_package_path

    def add_ios_reference(self, ios_reference, local_package_path):
        self.ios_references[ios_reference] = local_package_path
    
    def add_android_reference(self, android_reference, local_package_path):
        self.android_references[android_reference] = local_package_path

    def set_reference_path(self, logical_reference_path, reference_path):
        result = False
        for reference in self.android_references:
            if self.android_references[reference] == logical_reference_path:
                self.android_references[reference] = reference_path
                result = True
                break
        for reference in self.ios_references:
            if self.ios_references[reference] == logical_reference_path:
                self.ios_references[reference] = reference_path
                result = True
                break
        for reference in self.references:
            if self.references[reference] == logical_reference_path:
                self.references[reference] = reference_path
                result = True
                break
        return result

    def get_dependencies(self):
        result = []
        for dependency in self.dependencies:
            result.append(dependency)
        return result

    def get_reference_infos(self):
        result = []        
        for reference in self.references:
            result.append(ReferenceInfo(reference, self.references[reference]))
        return result

    def get_ios_reference_infos(self):
        result = []
        for reference in self.ios_references:
            result.append(ReferenceInfo(reference, self.ios_references[reference], self.ios_project_references[reference]))
        return result
    
    def get_android_reference_infos(self):
        result = []
        for reference in self.android_references:
            result.append(ReferenceInfo(reference, self.android_references[reference], self.android_project_references[reference]))
        return result

class ReferenceInfo:
    def __init__(self, reference, path, project_path):
        self.reference = reference
        self.path = path
        self.project_path = project_path
    
    def __str__(self):
        return self.reference + " " + self.path
    
    def __eq__(self, other):
        return self.reference == other.reference and self.path == other.path
    
    def __hash__(self):
        return hash(self.reference) ^ hash(self.path)

class PackageInfoBuilder:
    def __init__(self, repo_path, path_to_nuspec_files, path_to_nuget_bundle_config):
        self.path_to_nuspec_files = os.path.join(repo_path, path_to_nuspec_files)
        self.path_to_nuget_bundle_config = os.path.join(repo_path, path_to_nuget_bundle_config)
        self.repo_path = repo_path
    
    def build_packages(self):
        packages = dict()
        print(f"Process nuspec files in {self.path_to_nuspec_files}")
        nuspec_files = glob.glob(f"{self.path_to_nuspec_files}/*.nuspec", recursive=True)
        for nuspec_file in nuspec_files:
            package = self.read_nuspec_file(nuspec_file)
            if package is not None:
                packages[package.id] = package
        print(f"Process nuget bundle config file {self.path_to_nuget_bundle_config}")
        nuget_files = glob.glob(f"{self.path_to_nuget_bundle_config}/*.json", recursive=True)
        project_reference_dict = self.get_reference_project_dict(os.path.join(self.repo_path, "xamarin/maui"))
        for nuget_file in nuget_files:
            with open(nuget_file) as f:
                data = json.load(f)
                bundle = data["bundle"]
                id = bundle["id"]
                if id == "":
                    continue
                package = packages.get(id)                
                if package is None:
                    continue
                for component in bundle["components"]:
                    reference_path = os.path.join(self.repo_path, component["source"])
                    logical_path = self.trim_path(component["target"])
                    package.set_reference_path(logical_path, reference_path)
        #process all reference - if they not absolute path - make them absolute
        for package in packages.values():
            package.make_all_reference_paths_absolute(self.path_to_nuspec_files)
            for android_reference in package.android_references:
                if android_reference in project_reference_dict:
                    package.add_android_project_reference(android_reference, project_reference_dict[android_reference])
            for ios_reference in package.ios_references:
                if ios_reference in project_reference_dict:
                    package.add_ios_project_reference(ios_reference, project_reference_dict[ios_reference])
            
        return packages
    def get_reference_project_dict(self, projects_dir):
        result = dict()
        projects = glob.glob(f"{projects_dir}/**/*.csproj", recursive=True)
        for project in projects:
            project_name = os.path.basename(project)
            project_name = project_name.replace(".csproj", "")
            result[project_name] = project            
        return result
    def trim_path(self, path):
        if path.startswith(".\\"):
            path = path[2:]
        return self.normalize_path(path)

    def normalize_path(self, path):
        return path.replace("\\", "/")

    def get_reference_from_dll(self, dll_name):
        return dll_name.replace(".dll", "")

    def read_nuspec_file(self, nuspec_file):
        nuspec_tree = lxml.etree.parse(nuspec_file, parser=XMLParser(remove_blank_text=True))
        nuspec_root = nuspec_tree.getroot()
        default_namespace = {"ns":nuspec_root.nsmap[None]}
        nuspec_package_id = nuspec_root.xpath("//ns:package/ns:metadata/ns:id", namespaces=default_namespace)[0].text
        if not "maui" in nuspec_package_id.lower():
            return self.build_xamarin_package_info(nuspec_root, nuspec_package_id, default_namespace)
        return self.build_maui_package_info(nuspec_root, nuspec_package_id, default_namespace)

    def build_xamarin_package_info(self, nuspec_root, nuspec_package_id, default_namespace):
        package = MauiPackageInfo(nuspec_package_id)
        android_package_dependencies = nuspec_root.xpath("//ns:package/ns:metadata/ns:dependencies/ns:group[contains(@targetFramework, 'Android')]/ns:dependency/@id", namespaces=default_namespace)
        for dependency in android_package_dependencies:
            package.add_android_dependency(dependency)
        package_dependencies = nuspec_root.xpath("//ns:package/ns:metadata/ns:dependencies/ns:group[not(@targetFramework)]/ns:dependency/@id", namespaces=default_namespace)
        for dependency in package_dependencies:
            package.add_dependency(dependency)
        
        references = nuspec_root.xpath("//ns:package/ns:metadata/ns:references/ns:group[not(@targetFramework)]/ns:reference/@file", namespaces=default_namespace)
        ios_references = nuspec_root.xpath("//ns:package/ns:metadata/ns:references/ns:group[contains(@targetFramework, 'iOS')]/ns:reference/@file", namespaces=default_namespace)
        android_references = nuspec_root.xpath("//ns:package/ns:metadata/ns:references/ns:group[contains(@targetFramework, 'Android')]/ns:reference/@file", namespaces=default_namespace)

        files = nuspec_root.xpath("//ns:package/ns:files/ns:file", namespaces=default_namespace) 

        for file in files:
            source = file.get("src")
            target = file.get("target").lower()
            dll_name = os.path.basename(self.trim_path(source))
            if "ios" in target:
                if len(ios_references) == 0 and source.endswith(".dll"):
                    package.add_ios_reference(self.get_reference_from_dll(dll_name), self.trim_path(source))
                for ios_reference in ios_references:
                    if ios_reference in source:
                        package.add_ios_reference(self.get_reference_from_dll(ios_reference), self.trim_path(source))
                        break
            if "android" in target:
                if len(ios_references) == 0 and source.endswith(".dll"):
                    package.add_android_reference(self.get_reference_from_dll(dll_name), self.trim_path(source))
                for android_reference in android_references:
                    if android_reference in source:
                        package.add_android_reference(self.get_reference_from_dll(android_reference), self.trim_path(source))
                        break
            if "netstandard" in target:
                if len(ios_references) == 0 and source.endswith(".dll"):
                    package.add_reference(self.get_reference_from_dll(dll_name), self.trim_path(source))
                for reference in references:
                    if reference in source:
                        package.add_reference(self.get_reference_from_dll(reference), self.trim_path(source))
                        break   
        return package

    def build_maui_package_info(self, nuspec_root, nuspec_package_id, default_namespace):
        package = MauiPackageInfo(nuspec_package_id)
        package_dependencies = nuspec_root.xpath("//ns:package/ns:metadata/ns:dependencies/ns:group/ns:dependency/@id", namespaces=default_namespace)
        for dependency in package_dependencies:
            package.add_dependency(dependency)
            
        ios_references = nuspec_root.xpath("//ns:package/ns:metadata/ns:references/ns:group[contains(@targetFramework, 'ios')]/ns:reference/@file", namespaces=default_namespace)
        android_references = nuspec_root.xpath("//ns:package/ns:metadata/ns:references/ns:group[contains(@targetFramework, 'android')]/ns:reference/@file", namespaces=default_namespace)

        files = nuspec_root.xpath("//ns:package/ns:files/ns:file", namespaces=default_namespace) 
        
        for file in files:
            source = file.get("src")
            target = file.get("target")
            dll_name = os.path.basename(self.trim_path(source))
            if "ios" in target:
                if len(ios_references) == 0 and source.endswith(".dll"):
                    package.add_ios_reference(self.get_reference_from_dll(dll_name), self.trim_path(source))
                for ios_reference in ios_references:
                    if ios_reference in source:
                        package.add_ios_reference(self.get_reference_from_dll(ios_reference), self.trim_path(source))
                        break
            if "android" in target:
                if len(android_references) == 0 and source.endswith(".dll"):
                    package.add_android_reference(self.get_reference_from_dll(dll_name), self.trim_path(source))
                for android_reference in android_references:
                    if android_reference in source:
                        package.add_android_reference(self.get_reference_from_dll(android_reference), self.trim_path(source))
                        break    
        return package

class PackageStorage:
    def __init__(self, package_info_list):
        self.package_info_list = package_info_list

    def get_package_info_list(self):
        return self.package_info_list

    def get_package_info(self, package_id):
        if package_id in self.package_info_list:
            return self.package_info_list[package_id]
        return None 
    
    def get_dependent_packages(self, package_id):
        result = set()
        package_info = self.get_package_info(package_id)
        if package_info is None:
            return result
        dependencies = package_info.get_dependencies()
        if dependencies == None:
            return result
        for dependent_package_id in dependencies:
            result.add(dependent_package_id)
            dependent_packages = self.get_dependent_packages(dependent_package_id)
            if dependent_packages == None:
                continue
            result.update(dependent_packages)
        return result

    def find_common_references(self, package_references):
        common_references = set()
        packages_to_remove = []
        for package_reference in package_references:
            package = self.get_package_info(package_reference)
            if package == None:
                continue
            packages_to_remove.append(package.id)
            reference_info = package.get_reference_infos()
            common_references.update(reference_info)
            (dependent_references, _) = self.find_common_references(self.get_dependent_packages(package_reference))
            common_references.update(dependent_references)
        return (common_references, packages_to_remove)

    def find_android_references(self, package_references):
        android_references = set()
        packages_to_remove = []
        for package_reference in package_references:
            package = self.get_package_info(package_reference)
            if package == None:
                continue
            packages_to_remove.append(package.id)
            reference_info = package.get_android_reference_infos()
            android_references.update(reference_info)
            (dependent_references, _) = self.find_android_references(self.get_dependent_packages(package_reference))
            android_references.update(dependent_references)
        return (android_references, packages_to_remove)

    def find_ios_references(self, package_references):
        ios_references = set()
        packages_to_remove = []
        for package_reference in package_references:
            package = self.get_package_info(package_reference)
            if package == None:
                continue
            packages_to_remove.append(package.id)
            reference_info = package.get_ios_reference_infos()
            ios_references.update(reference_info)
            (dependent_references, _) = self.find_ios_references(self.get_dependent_packages(package_reference))
            ios_references.update(dependent_references)
        return (ios_references, packages_to_remove)

    def find_maui_references_to_process(self, package_references):
        android_references = set()
        ios_references = set()
        packages_to_remove = []
        for package_reference in package_references:
            package = self.get_package_info(package_reference)
            if package == None:
                continue
            packages_to_remove.append(package.id)
            android_references.update(package.get_android_reference_infos())
            ios_references.update(package.get_ios_reference_infos())
            (dependent_android_references, dependent_ios_references, _) = self.find_maui_references_to_process(self.get_dependent_packages(package_reference))
            android_references.update(dependent_android_references)
            ios_references.update(dependent_ios_references)
        return (android_references, ios_references, packages_to_remove)

    def get_maui_packages(self):
        result = []
        for package_info in self.package_info_list.values():
            if package_info.is_maui():
                result.append(package_info)
        return result

    def find_maui_packages(self, grouped_by_platform_references):
        maui_packages_to_process = set()
        references_to_remove = dict()
        references_to_remove["android"] = set()
        references_to_remove["ios"] = set()
        if "android" in grouped_by_platform_references:
            android_references = grouped_by_platform_references["android"]
            for package in self.get_maui_packages():
                references = package.get_android_reference_infos()
                for reference_info in references:
                    if reference_info.reference in android_references:
                        maui_packages_to_process.add(package.id)
                        references_to_remove["android"].add(reference_info.reference)
        if "ios" in grouped_by_platform_references:
            ios_references = grouped_by_platform_references["ios"]
            for package in self.get_maui_packages():
                references = package.get_ios_reference_infos()
                for reference_info in references:
                    if reference_info.reference in ios_references:
                        maui_packages_to_process.add(package.id)
                        references_to_remove["ios"].add(reference_info.reference)
        trimmed_packages = list(maui_packages_to_process)
        for package in maui_packages_to_process:
            dependent_packages = self.get_dependent_packages(package)
            for dependent_package in dependent_packages:
                if dependent_package in trimmed_packages:
                    trimmed_packages.remove(dependent_package)
        return (trimmed_packages, references_to_remove)