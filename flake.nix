{
  description = "Delphis: Dolphin Texture Manipulation Tool - Extraction, Tonemaps, Alpha Transparency, AI Upscaling & DDS Optimization";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      systems,
      flake-compat,
    }:
    let
      eachSystem =
        f:
        nixpkgs.lib.genAttrs (import systems) (
          system:
          f {
            inherit system;
            pkgs = import nixpkgs {
              inherit system;
              overlays = [ self.overlays.default ];
              config = {
                allowUnfree = true;
              };
            };
          }
        );
    in
    {
      overlays.default = import ./nix/overlay.nix;

      nixosModules = {
        default = import ./nix/nixos-module.nix;
        delphis = self.nixosModules.default;
      };

      homeManagerModules = {
        default = import ./nix/home-manager-module.nix;
        delphis = self.homeManagerModules.default;
      };

      packages = eachSystem (
        { pkgs, system }:
        rec {
          default = delphis;
          delphis = pkgs.delphis;
          dte = pkgs.dolphin-texture-extraction-tool;
          dolphin-texture-extraction-tool = pkgs.dolphin-texture-extraction-tool;
        }
      );

      apps = eachSystem (
        { pkgs, system }:
        let
          testApp = pkgs.writeShellApplication {
            name = "delphis-tests";
            runtimeInputs = [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  pyqt6
                  pillow
                  pytest
                  pytest-qt
                  setuptools
                ]
              ))
              pkgs.qt6.qtbase
            ];
            text = ''
              export QT_QPA_PLATFORM=offscreen
              export PYTHONPATH="''${PYTHONPATH:+$PYTHONPATH:}$PWD"
              pytest tests/ -v "$@"
            '';
          };
        in
        rec {
          default = delphis;
          delphis = {
            type = "app";
            program = "${pkgs.delphis}/bin/delphis";
            meta = {
              description = "Delphis: Dolphin Texture Manipulation Tool (GUI)";
            };
          };
          dte = {
            type = "app";
            program = "${pkgs.dolphin-texture-extraction-tool}/bin/dte";
            meta = {
              description = "DolphinTextureExtraction-tool CLI";
            };
          };
          test = {
            type = "app";
            program = "${testApp}/bin/delphis-tests";
            meta = {
              description = "Run automated test suite";
            };
          };
        }
      );

      checks = eachSystem (
        { pkgs, system }:
        {
          delphis-package = pkgs.delphis;
          dte-package = pkgs.dolphin-texture-extraction-tool;

          pytest = pkgs.stdenv.mkDerivation {
            pname = "delphis-pytest-check";
            version = "1.0.0";
            src = self;

            nativeBuildInputs = [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  pyqt6
                  pillow
                  pytest
                  pytest-qt
                  setuptools
                ]
              ))
              pkgs.qt6.qtbase
              pkgs.qt6.wrapQtAppsHook
            ];

            dontBuild = true;

            installPhase = ''
              mkdir -p $out
              export QT_QPA_PLATFORM=offscreen
              export HOME=$TMPDIR
              export PYTHONPATH=$PWD
              pytest tests/ -v
              touch $out/success
            '';
          };
        }
      );

      devShells = eachSystem (
        { pkgs, system }:
        {
          default = pkgs.mkShell {
            name = "delphis-dev-shell";

            packages = [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  pyqt6
                  pillow
                  pytest
                  pytest-qt
                  setuptools
                  wheel
                  black
                  ruff
                ]
              ))
              pkgs.qt6.qtbase
              pkgs.qt6.qtwayland
              pkgs.qt6.qtsvg
              pkgs.dolphin-texture-extraction-tool
              pkgs.realesrgan-ncnn-vulkan
              pkgs.imagemagick
              pkgs.nvidia-texture-tools
              pkgs.vulkan-tools
              pkgs.vulkan-loader
            ];

            shellHook = ''
              export QT_QPA_PLATFORM=wayland;xcb
              echo "🐬 Welcome to the Delphis development environment!"
              echo "Run 'pytest' to execute the test suite."
              echo "Run 'delphis' to launch the application."
            '';
          };
        }
      );
    };
}
