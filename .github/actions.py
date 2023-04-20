import os
import copy
from functools import cached_property
from pathlib import Path
import re
import shutil

from bs4 import BeautifulSoup


INDEX_FILE = "index.html"
TEMPLATE_FILE = "pkg_template.html"
YAML_ACTION_FILES = [".github/workflows/delete.yml", ".github/workflows/update.yml"]


def _read_env_var(key: str) -> str|None:
    """Try to get the given key from os.environ, returning None if the key doesn't exist

    :param key: The key to find
    :return: The value for the given key if present in the environment, else None
    """
    try:
        return os.environ[key]
    except KeyError:
        return None


class ActionInputs:
    """Container for different fields for actions read from the environment"""

    def __init__(self) -> None:
        self.action = _read_env_var("PKG_ACTION")
        self.pkg_name = _read_env_var("PKG_NAME")
        self.version = _read_env_var("PKG_VERSION")
        self.short_desc = _read_env_var("PKG_SHORT_DESC")
        self.long_desc = _read_env_var("PKG_LONG_DESC")
        self.homepage = _read_env_var("PKG_HOMEPAGE")
        self.link = _read_env_var("PKG_LINK")

    @cached_property
    def norm_pkg_name(self) -> str|None:
        """Normalized name string based on PEP503: https://www.python.org/dev/peps/pep-0503/"""
        return re.sub(r"[-_.]+", "-", self.pkg_name).lower() if self.pkg_name else None

    @cached_property
    def pkg_index(self) -> Path:
        return Path(self.norm_pkg_name) / INDEX_FILE

    def pkg_exists(self, root_soup: BeautifulSoup) -> bool:
        """Determine if norm_pkg_name can be found in the given root index.html doc soup

        :param root_soup: The BeautifulSoup to search
        :return: True if the package name exists, else False
        """
        package_ref = self.norm_pkg_name + '/'
        for anchor in root_soup.find_all('a'):
            if anchor["href"] == package_ref:
                return True
        return False

    def pkg_version_exists(self, pkg_soup: BeautifulSoup) -> bool:
        egg = f"#egg={self.norm_pkg_name}-{self.version}"
        anchors = pkg_soup.find_all('a')

        for anchor in anchors:
            if anchor["href"].endswith(egg):
                return True

        return False


def _add_pkg_to_root(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    # Copy the last anchor element
    last_anchor = root_soup.find_all('a')[-1]
    new_anchor = copy.copy(last_anchor)
    new_anchor["href"] = f"{inputs.norm_pkg_name}/"
    new_anchor.contents[0].replace_with(inputs.pkg_name)

    # Modify spans for the anchor to contain the version and description of the new package
    spans = new_anchor.find_all("span")
    spans[1].string = inputs.version
    spans[2].string = inputs.short_desc

    # Add it to our index and save it
    last_anchor.insert_after(new_anchor)

    with open(INDEX_FILE, "wb") as index:
        index.write(root_soup.prettify("utf-8"))


def _write_template(inputs: ActionInputs, template_file: str = TEMPLATE_FILE) -> None:
    with open(template_file, encoding="utf-8") as template_fh:
        template = template_fh.read()

    template = template.replace("_package_name", inputs.pkg_name)
    template = template.replace("_version", inputs.version)
    template = template.replace("_link", f"{inputs.link}#egg={inputs.norm_pkg_name}-{inputs.version}")
    template = template.replace("_homepage", inputs.homepage)
    template = template.replace("_long_description", inputs.long_desc)

    os.mkdir(inputs.norm_pkg_name)

    with open(inputs.pkg_index, "w", encoding="utf-8") as f:
        f.write(template)


def register(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    # Read the root-level index.html into a BeautifulSoup object
    if inputs.pkg_exists(root_soup):
        raise ValueError(f"Package {inputs.norm_pkg_name} already exists")

    # Create a new anchor element for our new package and add it to the page
    _add_pkg_to_root(inputs, root_soup)

    # Then get the template, replace the content and write to the right place
    _write_template(inputs)


def _update_root_pkg_version(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    # Change the version in the root index
    anchor = root_soup.find('a', attrs={"href": f"{inputs.norm_pkg_name}/"})
    spans = anchor.find_all("span")
    spans[1].string = inputs.version

    with open(INDEX_FILE, "wb") as index:
        index.write(root_soup.prettify("utf-8"))


def _add_new_pkg_version(inputs: ActionInputs, pkg_soup: BeautifulSoup) -> None:
    # Create a new anchor element for our new version using the last anchor element as a baseline
    last_anchor = pkg_soup.find_all('a', href=re.compile("#egg"))[-1]
    new_anchor = copy.copy(last_anchor)
    new_anchor["href"] = f"{inputs.link}#egg={inputs.norm_pkg_name}-{inputs.version}"

    # Add the new anchor to the end of the list
    last_anchor.insert_after(new_anchor)

    # Change the latest version to point to the new one
    pkg_soup.html.body.div.section.find_all("span")[1].contents[0].replace_with(inputs.version)

    with open(inputs.pkg_index, "wb") as index:
        index.write(pkg_soup.prettify("utf-8"))


def add(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    if not inputs.pkg_exists(root_soup):
        raise ValueError(f"Package {inputs.norm_pkg_name} does not exist")

    with open(inputs.pkg_index, 'r', encoding="utf-8") as html_file:
        pkg_soup = BeautifulSoup(html_file, "html.parser")

    if inputs.pkg_version_exists(pkg_soup):
        raise ValueError(f"Package {inputs.norm_pkg_name} version {inputs.version} already present")

    _update_root_pkg_version(inputs, root_soup)

    _add_new_pkg_version(inputs, pkg_soup)


def _update_pkg_version(inputs: ActionInputs, pkg_soup: BeautifulSoup) -> None:
    egg = f"#egg={inputs.norm_pkg_name}-{inputs.version}"
    anchors = pkg_soup.find_all('a')

    for anchor in anchors:
        if anchor["href"].endswith(egg):
            anchor["href"] = f"{inputs.link}{egg}"
            break

    with open(inputs.pkg_index, "wb") as index:
        index.write(pkg_soup.prettify("utf-8"))


def update(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    if not inputs.pkg_exists(root_soup):
        raise ValueError(f"Package {inputs.norm_pkg_name} does not exist")

    with open(inputs.pkg_index, 'r', encoding="utf-8") as html_file:
        pkg_soup = BeautifulSoup(html_file, "html.parser")

    _update_pkg_version(inputs, pkg_soup)


def delete(inputs: ActionInputs, root_soup: BeautifulSoup) -> None:
    if not inputs.pkg_exists(root_soup):
        raise ValueError(f"Package {inputs.norm_pkg_name} must be registered first")

    # Remove the package directory
    shutil.rmtree(inputs.norm_pkg_name)

    # Find and remove the anchor corresponding to our package
    anchor = root_soup.find('a', attrs={"href": f"{inputs.norm_pkg_name}/"})
    anchor.extract()
    with open(INDEX_FILE, "wb") as index:
        index.write(root_soup.prettify("utf-8"))


def main():
    # Call the right method, with the right arguments
    action_inputs = ActionInputs()

    with open(INDEX_FILE, 'r', encoding="utf-8") as root_index_fh:
        root_soup = BeautifulSoup(root_index_fh, "html.parser")

    match action_inputs.action:
        case "REGISTER":
            register(action_inputs, root_soup)
        case "ADD":
            add(action_inputs, root_soup)
        case "UPDATE":
            update(action_inputs, root_soup)
        case "DELETE":
            delete(action_inputs, root_soup)


if __name__ == "__main__":
    main()
