# OpenWrt Builder profiles

Each directory under `profiles/` is one public build profile. The directory name is the profile ID passed to `scripts/build.py` and selected from the GitHub Actions build dropdown.

## Naming contract

Profile IDs are mandatory and versioned:

```text
<device>-<X.Y.Z|X.Y|snapshot>
```

The suffix is semantic:

- `X.Y.Z` means an exact OpenWrt release, for example `archer-a9-v6-25.12.5`.
- `X.Y` means the moving stable branch for that release line, for example `archer-a9-v6-25.12` using an `openwrt-25.12...` ref.
- `snapshot` means the OpenWrt development snapshot (`REF=main`) or a `/snapshots/` ImageBuilder.

Build implementation is deliberately not part of the public profile ID. `imagebuilder`, `release-patched`, `selective-source`, and `full-source` belong in `settings` because they describe how the firmware is produced, not which firmware profile the user selected.

## Required profile files

Every profile directory must contain:

```text
README.md
settings
packages
feeds
git-packages
```

`source-build-targets` is allowed only for `release-patched` profiles and is mandatory there. `files/` is optional for embedded root filesystem files.

The catalog validator reuses the builder's normal settings/package/feed parsers and also checks the profile name against the configured OpenWrt source:

- exact release IDs must match `BASE_REF`, exact `REF`, or the ImageBuilder release URL;
- stable `X.Y` IDs must match an `openwrt-X.Y...` source ref and cannot pin a point-release SDK URL;
- `snapshot` source profiles must use `REF=main`, while snapshot ImageBuilder profiles must use `/snapshots/` URLs;
- unknown profile files, symlinks, malformed settings, duplicate packages, invalid feeds and invalid Git package declarations fail validation.

Run:

```bash
python3 scripts/validate-profile-catalog.py
python3 tests/test_profile_catalog.py
```

The normal Docker validation workflow runs these checks automatically.

## GitHub Actions dropdown

`.github/workflows/build.yml` contains generated profile choices between marker comments. Do not maintain that list by hand.

`scripts/sync-profile-workflow.py` validates the catalog and regenerates the dropdown. Pull-request CI verifies the generator. After profile-related changes land on `main`, `.github/workflows/sync-profile-options.yml` regenerates and publishes the choices automatically.

Automatic publication requires repository secret `PROFILE_SYNC_TOKEN`, scoped to this repository with permission to update repository contents and workflow files. The sync workflow only uses the credential on `main`.

## Current examples

```text
archer-a9-v6-25.12.5
archer-a9-v6-25.12
linksys-velop-whw03-v2-25.12.5
x86-64-24.10.5
x86-64-25.12.5
x86-64-snapshot
```
