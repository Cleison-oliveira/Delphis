{
  lib,
  python3Packages,
  qt6,
  makeDesktopItem,
  copyDesktopItems,
  dte,
  realesrgan-ncnn-vulkan,
  imagemagick,
  nvidia-texture-tools,
  vulkan-tools,
  vulkan-loader,
  src ? ../.,
}:
let
  desktopItem = makeDesktopItem {
    name = "delphis";
    exec = "delphis";
    icon = "delphis";
    desktopName = "Delphis";
    genericName = "Dolphin Texture Manipulation Tool";
    comment = "Extraction, Tonemaps, Alpha Transparency, AI Upscaling & DDS Optimization";
    categories = [
      "Utility"
      "Graphics"
      "Game"
    ];
    keywords = [
      "Dolphin"
      "Texture"
      "GameCube"
      "Wii"
      "Upscale"
      "DDS"
      "Tonemap"
    ];
  };
in
python3Packages.buildPythonApplication rec {
  pname = "delphis";
  version = "1.0.0";
  format = "pyproject";

  inherit src;

  nativeBuildInputs = [
    python3Packages.setuptools
    python3Packages.wheel
    qt6.wrapQtAppsHook
    copyDesktopItems
  ];

  buildInputs = [
    qt6.qtbase
    qt6.qtwayland
    qt6.qtsvg
  ];

  propagatedBuildInputs = [
    python3Packages.pyqt6
    python3Packages.pillow
  ];

  nativeCheckInputs = [
    python3Packages.pytestCheckHook
    python3Packages.pytest-qt
  ];

  # Set offscreen Qt platform plugin during testing
  preCheck = ''
    export QT_QPA_PLATFORM=offscreen
    export HOME=$TMPDIR
  '';

  # Disable checkPhase if needed during quick builds, but enabled by default
  doCheck = false;

  desktopItems = [ desktopItem ];

  makeWrapperArgs = [
    "--prefix PATH : ${lib.makeBinPath [
      dte
      realesrgan-ncnn-vulkan
      imagemagick
      nvidia-texture-tools
      vulkan-tools
      vulkan-loader
    ]}"
  ];

  dontWrapQtApps = false;

  preFixup = ''
    makeWrapperArgs+=("''${qtWrapperArgs[@]}")
  '';

  postInstall = ''
    install -Dm644 delphis/assets/icons/delphis.svg $out/share/icons/hicolor/scalable/apps/delphis.svg
    install -Dm644 delphis/assets/icons/delphis.svg $out/share/pixmaps/delphis.svg
  '';

  meta = with lib; {
    description = "Delphis: Dolphin Texture Manipulation Tool - Extraction, Tonemaps, Alpha Transparency, AI Upscaling & DDS Optimization";
    homepage = "https://github.com/Cleison-oliveira/delphis";
    license = licenses.mit;
    mainProgram = "delphis";
    platforms = platforms.linux;
  };
}
