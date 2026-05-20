{
  description = "hypothesis-swarm — swarm testing for Hypothesis";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      pkgsFor = sys: import nixpkgs { system = sys; };
    in {
      devShells = forAllSystems (system:
        let pkgs = pkgsFor system;
        in {
          default = pkgs.mkShell {
            packages = [ pkgs.uv pkgs.ruff pkgs.pyright pkgs.just ];
          };
        });

      packages = forAllSystems (system:
        let pkgs = pkgsFor system;
        in {
          # For development, prefer `nix develop` + uv.
          default = pkgs.python3Packages.buildPythonPackage {
            pname = "hypothesis-swarm";
            version = "0.1.0";
            src = ./.;
            format = "pyproject";
            # TODO: add propagatedBuildInputs once we pin Hypothesis.
          };
        });
    };
}
