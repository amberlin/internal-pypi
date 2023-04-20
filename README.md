<h1 align="center">Sequencing Health internal-pypi</h1>

---

<p align="center">
  <a href="#Description">Description</a> •
  <a href="#Actions">Actions</a> •
  <a href="#Name-Collisions">Name Collisions</a> •
  <a href="#Supply-Chain-Attacks">A word about supply chain attacks</a> •
  <a href="#References">References</a>
</p>

---

## Description

This repository is a Github page used as a PyPI index, which conforms to [PEP503](https://www.python.org/dev/peps/pep-0503/).

---

_Private packages indexed here are kept private: you will need relevant GitHub authentication to be able to retrieve each package._

## Actions

Five GitHub Actions workflows exist in this repository.
Four of them are triggered via `workflow_dispatch`, and one via `workflow_call`.
Together, the `workflow_dispatch` workflows let you register or delete packages, add new package versions, or update existing package versions.
These workflows do not automatically update the package index, but rather automatically open a pull request with the changes required to update the index.
The `workflow_call` workflow is intended to automatically add new package versions from a calling repository.
Before this workflow can be used, the package *must* be manually registered.

### Register

`workflow_dispatch` workflow to register a new package in the index.
Requires a package name, initial version, short description, long description, GitHub homepage, and installation link.

### Add

`workflow_dispatch` workflow to add a new version of a package to the index.
Requires a package name, new version, and installation link.

### Update

`workflow_dispatch` workflow to update an existing version of a package in place with a new installation link.
Requires a package name, version, and new installation link.

### Delete

`workflow_dispatch` workflow to delete a package from the index.
Requires a package name.

### Auto

`workflow_call` workflow to add a new version of a package to the index.
Requires a package name, version, and installation link.

## Name Collisions

A private package's name might already exist in the public package index.
By changing the order in which `pip` looks at package indices, you can guarantee installation from this package index rather than the public one.
This requires the addition of `--index-url https://genapsysinc.github.io/internal-pypi` to `pip install` commands when installing a specific package in this index, or the addition of `--index-url https://genapsysinc.github.io/internal-pypi --extra-index-url https://pypi.org/simple` when installing a mixture of private and public packages.
*DO NOT* just do `--extra-index-url https://genapsysinc.github.io/internal-pypi`, as this allows supply chain attacks to happen!

## Supply Chain Attacks

A supply chain attack can occur when a private package name has a collision with a public one.
For example, let's say you have a package named `fbi_package` version `2.8.3` hosted on privately here.
An attacker could create a malicious package with the same name and a higher version (for example `99.0.0`).
When you run `pip install fbi_package --extra-index-url https://genapsysinc.github.io/internal-pypi`, under the hood `pip` will download the latest version of the package, which is the malicious package!

Since this GitHub page is *private*, this is unlikely to occur, but the risk does exist, and caution should be taken.

## References

Taken directly from https://github.com/astariul/github-hosted-pypi

"**This is greatly inspired from [this repository](https://github.com/ceddlyburge/python-package-server).**
It's just a glorified version, with cleaner pages and github actions for easily adding, updating and removing packages from your index.

Also check the [blogpost](https://www.freecodecamp.org/news/how-to-use-github-as-a-pypi-server-1c3b0d07db2/) of the original author!"
