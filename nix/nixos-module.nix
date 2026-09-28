{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.delphis;
in
{
  options.programs.delphis = {
    enable = lib.mkEnableOption "Delphis: Dolphin Texture Manipulation Tool";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.delphis;
      description = "The Delphis package to install.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [
      cfg.package
    ];
  };
}
