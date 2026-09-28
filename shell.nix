# Flake compatibility development shell for nix-shell
let
  compat = import ./default.nix;
  pkgs = compat.inputs.nixpkgs.legacyPackages.${builtins.currentSystem};
in
compat.devShells.${builtins.currentSystem}.default
