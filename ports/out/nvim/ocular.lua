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
        rosewater = "#d7c2bf",
        flamingo = "#e3bebe",
        pink = "#eab8dc",
        mauve = "#d9b9ff",
        red = "#ffb1c4",
        maroon = "#feb2be",
        peach = "#feb78a",
        yellow = "#dbc492",
        green = "#99d694",
        teal = "#87d4c8",
        sky = "#80d3e1",
        sapphire = "#7dd1f6",
        blue = "#a7c8ff",
        lavender = "#bac4ff",
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
        rosewater = "#8f4536",
        flamingo = "#993c3f",
        pink = "#8d3d78",
        mauve = "#684c9e",
        red = "#9b393f",
        maroon = "#9a393e",
        peach = "#983f15",
        yellow = "#835000",
        green = "#276819",
        teal = "#00656a",
        sky = "#006188",
        sapphire = "#006474",
        blue = "#3259a4",
        lavender = "#4655a5",
      },
    },
  },
  config = function(_, opts)
    require("catppuccin").setup(opts)
    vim.cmd.colorscheme("catppuccin")
  end,
}
