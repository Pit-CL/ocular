-- Ocular — lazy.nvim spec para catppuccin/nvim
-- Rooibos (dark) -> flavour "mocha" · Manzanilla (light) -> flavour "latte".
-- API verificada 2026-07-26 contra github.com/catppuccin/nvim README:
--   color_overrides = { all = {...}, mocha = {...}, latte = {...} }
--   flavour = "auto" + background = { light = "latte", dark = "mocha" }
return {
  "catppuccin/nvim",
  name = "catppuccin",
  priority = 1000,
  opts = {
    flavour = "auto",
    background = {
      light = "latte",
      dark = "mocha",
    },
    color_overrides = {
      mocha = {
        crust = "#15110d",
        mantle = "#191511",
        base = "#1e1a15",
        surface0 = "#2b2520",
        surface1 = "#38322b",
        surface2 = "#453f38",
        text = "#dfd9cc",
        subtext1 = "#d1cbc0",
        subtext0 = "#c6c1b7",
        overlay2 = "#b4afa8",
        overlay1 = "#a6a099",
        overlay0 = "#98938d",
        rosewater = "#efc7bf",
        flamingo = "#ecb4c0",
        pink = "#fab1d9",
        mauve = "#e4b1f4",
        red = "#ffb2b1",
        maroon = "#f6b49d",
        peach = "#feb782",
        yellow = "#eecd7c",
        green = "#a5ce92",
        teal = "#6ed8d0",
        sky = "#7fdfef",
        sapphire = "#7bc6f6",
        blue = "#a5c9ff",
        lavender = "#d0cbff",
      },
      latte = {
        crust = "#e6e0d7",
        mantle = "#eee8df",
        base = "#f5efe7",
        surface0 = "#e3ddd4",
        surface1 = "#d9d3c9",
        surface2 = "#cdc6bd",
        text = "#3f372d",
        subtext1 = "#544c43",
        subtext0 = "#675f57",
        overlay2 = "#817a73",
        overlay1 = "#918b84",
        overlay0 = "#a19c94",
        rosewater = "#69433c",
        flamingo = "#884f5d",
        pink = "#8c406e",
        mauve = "#824992",
        red = "#983c41",
        maroon = "#914e36",
        peach = "#8c4900",
        yellow = "#614a00",
        green = "#3f6b26",
        teal = "#006561",
        sky = "#005460",
        sapphire = "#006d9d",
        blue = "#2c5aa3",
        lavender = "#4f4480",
      },
    },
  },
  config = function(_, opts)
    require("catppuccin").setup(opts)
    vim.cmd.colorscheme("catppuccin")
  end,
}
