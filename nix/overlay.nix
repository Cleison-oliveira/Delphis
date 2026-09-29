final: prev: {
  dolphin-texture-extraction-tool = prev.callPackage ./dte.nix {
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
          || baseName == "bin"
          || baseName == "obj"
          || baseName == "__pycache__"
          || baseName == ".pytest_cache"
        );
    };
  };
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
          || baseName == "bin"
          || baseName == "obj"
          || baseName == "__pycache__"
          || baseName == ".pytest_cache"
        );
    };
  };
}
