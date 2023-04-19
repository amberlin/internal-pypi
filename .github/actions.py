import os
import copy
from pathlib import Path
import re
import shutil

from bs4 import BeautifulSoup


INDEX_FILE = "index.html"
TEMPLATE_FILE = "pkg_template.html"
YAML_ACTION_FILES = [".github/workflows/delete.yml", ".github/workflows/update.yml"]


def normalize(name: str) -> str:
    """Normalize name string according to PEP503: https://www.python.org/dev/peps/pep-0503/

    :param name: The name string
    :return: The normalized name string based on PEP503
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def package_exists(soup: BeautifulSoup, pkg_name: str) -> bool:
    """Determine if the given package_name can be found in the given HTML doc soup

    :param soup: The BeautifulSoup to search
    :param pkg_name: The package name to search for
    :return: True if the package name exists, else False
    """
    package_ref = pkg_name + '/'
    for anchor in soup.find_all('a'):
        if anchor["href"] == package_ref:
            return True
    return False


def register(pkg_name: str, version: str, short_desc: str, long_desc: str, homepage: str, link: str) -> None:
    # Read the root-level index.html into a BeautifulSoup object
    with open(INDEX_FILE, 'r', encoding="utf8") as html_file:
        soup = BeautifulSoup(html_file, "html.parser")

    norm_pkg_name = normalize(pkg_name)

    if package_exists(soup, norm_pkg_name):
        raise ValueError(f"Package {norm_pkg_name} seems to already exists")

    # Create a new anchor element for our new package

    # Copy the last anchor element
    last_anchor = soup.find_all('a')[-1]
    new_anchor = copy.copy(last_anchor)
    new_anchor["href"] = f"{norm_pkg_name}/"
    new_anchor.contents[0].replace_with(pkg_name)

    # Modify spans for the anchor to contain the version and description of the new package
    spans = new_anchor.find_all("span")
    spans[1].string = version
    spans[2].string = short_desc

    # Add it to our index and save it
    last_anchor.insert_after(new_anchor)
    with open(INDEX_FILE, "wb") as index:
        index.write(soup.prettify("utf-8"))

    # Then get the template, replace the content and write to the right place
    with open(TEMPLATE_FILE, encoding="utf-8") as temp_file:
        template = temp_file.read()

    template = template.replace("_package_name", pkg_name)
    template = template.replace("_version", version)
    template = template.replace("_link", f"{link}#egg={norm_pkg_name}-{version}")
    template = template.replace("_homepage", homepage)
    template = template.replace("_long_description", long_desc)

    os.mkdir(norm_pkg_name)
    package_index = Path(norm_pkg_name) / INDEX_FILE
    with open(package_index, "w", encoding="utf-8") as f:
        f.write(template)


def add(pkg_name: str, version: str, link: str) -> None:
    # Read our index first
    with open(INDEX_FILE) as html_file:
        soup = BeautifulSoup(html_file, "html.parser")
    norm_pkg_name = normalize(pkg_name)

    if not package_exists(soup, norm_pkg_name):
        raise ValueError("Package {} seems to not exists".format(norm_pkg_name))

    # Change the version in the main page
    anchor = soup.find('a', attrs={"href": "{}/".format(norm_pkg_name)})
    spans = anchor.find_all('span')
    spans[1].string = version
    with open(INDEX_FILE, 'wb') as index:
        index.write(soup.prettify("utf-8"))

    # Change the package page
    index_file = os.path.join(norm_pkg_name, INDEX_FILE)
    with open(index_file) as html_file:
        soup = BeautifulSoup(html_file, "html.parser")

    # Create a new anchor element for our new version
    last_anchor = soup.find_all('a')[-1]        # Copy the last anchor element
    new_anchor = copy.copy(last_anchor)
    new_anchor['href'] = "{}#egg={}-{}".format(link, norm_pkg_name, version)

    # Add it to our index
    last_anchor.insert_after(new_anchor)

    # Change the latest version
    soup.html.body.div.section.find_all('span')[1].contents[0].replace_with(version)

    # Save it
    with open(index_file, "wb") as index:
        index.write(soup.prettify("utf-8"))

def update(pkg_name, version, link):
    pass


def delete(pkg_name):
    # Read our index first
    with open(INDEX_FILE, encoding="utf-8") as html_file:
        soup = BeautifulSoup(html_file, "html.parser")
    norm_pkg_name = normalize(pkg_name)

    if not package_exists(soup, norm_pkg_name):
        raise ValueError(f"Package {norm_pkg_name} must be registered first")

    # Remove the package directory
    shutil.rmtree(norm_pkg_name)

    # Find and remove the anchor corresponding to our package
    anchor = soup.find('a', attrs={"href": f"{norm_pkg_name}/"})
    anchor.extract()
    with open(INDEX_FILE, "wb") as index:
        index.write(soup.prettify("utf-8"))


def main():
    # Call the right method, with the right arguments
    action = os.environ["PKG_ACTION"]

    match action:
        case "REGISTER":
            register(
                pkg_name=os.environ["PKG_NAME"],
                version=os.environ["PKG_VERSION"],
                short_desc=os.environ["PKG_SHORT_DESC"],
                long_desc=os.environ["PKG_LONG_DESC"],
                homepage=os.environ["PKG_HOMEPAGE"],
                link=os.environ["PKG_LINK"],
            )
        case "ADD":
            add(
                pkg_name=os.environ["PKG_NAME"],
                version=os.environ["PKG_VERSION"],
                link=os.environ["PKG_LINK"],
            )
        case "UPDATE":
            update(
                pkg_name=os.environ["PKG_NAME"],
                version=os.environ["PKG_VERSION"],
                link=os.environ["PKG_LINK"],
            )
        case "DELETE":
            delete(pkg_name=os.environ["PKG_NAME"])


if __name__ == "__main__":
    main()
