vim.opt.number = true
vim.opt.relativenumber = true

vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.autoindent = true
vim.opt.smartindent = true

vim.opt.clipboard = "unnamedplus"

vim.opt.ignorecase = true -- case insensitive search
vim.opt.smartcase = true -- case sensitive if uppercase in string
vim.opt.hlsearch = true -- highlight search matches
vim.opt.incsearch = true -- show matches as you type

vim.opt.undofile = true

vim.opt.cursorline = true -- highlight current line
vim.opt.scrolloff = 5 -- keep x lines above/below cursor
vim.opt.sidescrolloff = 5 -- keep x lines to left/right of cursor

vim.opt.showmatch = true -- highlights matching brackets

vim.opt.autoread = true -- auto-reload changes if outside of neovim

vim.opt.path:append("**") -- include subdirs in search

-- Folding: requires treesitter available at runtime; safe fallback if not
vim.opt.foldmethod = "expr" -- use expression for folding
vim.opt.foldexpr = "v:lua.vim.treesitter.foldexpr()" -- use treesitter for folding
vim.opt.foldlevel = 99 -- start with all folds open


-- ============================================================================
-- KEYMAPS
-- ============================================================================
vim.g.mapleader = " " -- space for leader
vim.g.maplocalleader = " " -- space for localleader

-- Clear search highlights by pressing Esc
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>', { silent = true, desc = 'Clear search highlights' })

vim.keymap.set({ "n", "v" }, "<leader>x", '"_d', { desc = "Delete without yanking" })

vim.keymap.set("v", "<", "<gv", { desc = "Indent left and reselect" })
vim.keymap.set("v", ">", ">gv", { desc = "Indent right and reselect" })

-- Different behavior for editing prose
vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "text", "gitcommit" },
    callback = function()
        vim.opt_local.wrap = true
        vim.opt_local.linebreak = true
        vim.opt_local.breakindent = true
        vim.opt_local.spell = true
        vim.keymap.set("n", "j", "gj", { buffer = true })
        vim.keymap.set("n", "k", "gk", { buffer = true })

        vim.opt_local.formatoptions:append("r") -- `<CR>` in insert mode
		vim.opt_local.formatoptions:append("o") -- `o` in normal mode
		vim.opt_local.comments = {
			"b:- [ ]", -- tasks
			"b:- [x]",
			"b:*", -- unordered list
			"b:-",
			"b:+",
		}
        vim.keymap.set("i", "<CR>", function()
            local line = vim.api.nvim_get_current_line()
            -- Matches any leading whitespace followed by digits and a dot/space
            local num = line:match("^%s*(%d+)%.%s+")
            if num then
                return "<CR>" .. (num + 1) .. ". "
            end
            -- Fallback to normal Enter behavior (which still catches your unordered comments)
            return "<CR>"
        end, { expr = true, buffer = true })
    end,
})

-- return to last cursor position
vim.api.nvim_create_autocmd("BufReadPost", {
	group = augroup,
	desc = "Restore last cursor position",
	callback = function()
		if vim.o.diff then -- except in diff mode
			return
		end

		local last_pos = vim.api.nvim_buf_get_mark(0, '"') -- {line, col}
		local last_line = vim.api.nvim_buf_line_count(0)

		local row = last_pos[1]
		if row < 1 or row > last_line then
			return
		end

		pcall(vim.api.nvim_win_set_cursor, 0, last_pos)
	end,
})

-- highlight yanked text
vim.api.nvim_create_autocmd("TextYankPost", {
	group = augroup,
	callback = function()
		vim.hl.on_yank()
	end,
})


-- ============================================================================
-- PLUGINS (vim.pack)
-- ============================================================================
vim.pack.add({
  'https://github.com/echasnovski/mini.nvim'
})

require('mini.ai').setup()       
require('mini.surround').setup() 
require('mini.pairs').setup()    
require('mini.comment').setup()  
require('mini.files').setup()
require('mini.git').setup()

-- Map <Leader>e to open the file explorer
vim.keymap.set('n', '<leader>e', function() require('mini.files').open() end, { desc = "Open mini.files" })

local statusline = require('mini.statusline')

-- Define the custom word count function
local function get_word_count()
  local ft = vim.bo.filetype
  if ft == "markdown" or ft == "text" or ft == "gitcommit" then
    local words = vim.fn.wordcount().words
    return tostring(words) .. " words"
  end
  return ""
end

statusline.setup({
  content = {
    active = function()
      local mode, mode_hl = statusline.section_mode({ trunc_width = 120 })
      local git           = statusline.section_git({ trunc_width = 40 })
      local diff          = statusline.section_diff({ trunc_width = 75 })
      local diagnostics   = statusline.section_diagnostics({ trunc_width = 75 })
      local lsp           = statusline.section_lsp({ trunc_width = 75 })
      local filename      = statusline.section_filename({ trunc_width = 140 })
      local search        = statusline.section_searchcount({ trunc_width = 75 })

      local filepath = "%f"
      
      -- Fetch word count
      local wc = get_word_count()

      -- Custom location format replacing the | with / and adding L/C labels
      local location = "%L lines %l:%c"

      return statusline.combine_groups({
        { hl = mode_hl,                  strings = { mode } },
        { hl = 'MiniStatuslineDevinfo',  strings = { git, diff, diagnostics, lsp } },
        '%<', 
        { hl = 'MiniStatuslineFilename', strings = { filepath } },
        '%=', 
        -- Place the word count exactly where the fileinfo used to be
        { hl = 'MiniStatuslineFileinfo', strings = { wc } },
        { hl = mode_hl,                  strings = { search } },
        { hl = 'MiniStatuslineFilename', strings = { location } },
      })
    end
  }
})
