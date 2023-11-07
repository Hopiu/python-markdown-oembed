{
  description = "Oembed plugin flake";
  inputs = {
    nixpkgs.url = github:NixOS/nixpkgs/nixos-unstable;
  };
  outputs = { self, nixpkgs }:
  let
    pkgs = import nixpkgs {
        inherit system;
        overlays = [];
    };
    pythonPackages = pkgs.python3Packages;
    system = "x86_64-linux";
  in rec {
    devShell.x86_64-linux = pkgs.mkShell {
      buildInputs = [
        pkgs.python3
        pkgs.python3Packages.pip
      ];
      shellHook = ''
        export PS1='\u@md-oembed \$ '
        export PIP_PREFIX=$(pwd)/venv/pip_packages
        export PYTHONPATH="$PIP_PREFIX/${pkgs.python3.sitePackages}:$PYTHONPATH"
        export PATH="$PIP_PREFIX/bin:$PATH"
        unset SOURCE_DATE_EPOCH
      '';
    };
  };
}
