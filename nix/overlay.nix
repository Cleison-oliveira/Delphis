final: prev: {
  dolphin-texture-extraction-tool = prev.callPackage ./dte.nix { };
  dte = final.dolphin-texture-extraction-tool;

  delphis = final.callPackage ./delphis.nix {
    dte = final.dte;
    src = final.lib.cleanSourceWith {
      src = ../.;
      filter =
        path: type:
        let
          baseName = baseNameOf path;
        in
        !(
          baseName == ".git"
          || baseName == "result"
          || baseName == "dist"
          || baseName == "build"
          || final.lib.hasSuffix ".egg-info" baseName
          || baseName == "__pycache__"
          || baseName == ".pytest_cache"
        );
    };
  };
}
