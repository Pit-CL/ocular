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
        rosewater = "#e2bfb9",
        flamingo = "#f1b8c2",
        pink = "#fab1d9",
        mauve = "#deb7fc",
        red = "#ffb4ad",
        maroon = "#f1baa1",
        peach = "#feb782",
        yellow = "#e3c372",
        green = "#a4d399",
        teal = "#70d8cb",
        sky = "#7ad2ed",
        sapphire = "#89cdff",
        blue = "#aac8ff",
        lavender = "#c7bffb",
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
        rosewater = "#77534e",
        flamingo = "#834b57",
        pink = "#8c406e",
        mauve = "#744991",
        red = "#9a3b38",
        maroon = "#854d32",
        peach = "#8c4900",
        yellow = "#725800",
        green = "#326726",
        teal = "#00665e",
        sky = "#006379",
        sapphire = "#006090",
        blue = "#3458a3",
        lavender = "#5d5391",
      },
    },
  },
  config = function(_, opts)
    require("catppuccin").setup(opts)
    vim.cmd.colorscheme("catppuccin")
  end,
}
