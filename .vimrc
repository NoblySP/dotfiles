set nocompatible
set number relativenumber
set tabstop=4
set softtabstop=4
set shiftwidth=4
set hlsearch " highlight search results
set expandtab " turn tabs into spaces
set autoindent
set smartindent
syntax enable

" Force cursor shape changes using terminal escape codes
let &t_SI = "\<Esc>[6 q" " Set cursor to a steady vertical bar on entering Insert mode
let &t_EI = "\<Esc>[2 q" " Set cursor to a block on leaving Insert mode

" Remap y to yank to the system clipboard register (+)
set clipboard=unnamedplus
" nnoremap y "+y
" vnoremap y "+y
" nnoremap Y "+Y

" Clear search higlights by pressing Enter/CR
nnoremap <silent> <CR> :nohlsearch<CR><CR>

" Fold
set foldmethod=indent  " Change to syntax if you want the top line to be folded as well
set nofoldenable  " Keep all folds open when a file is opened
set foldlevelstart=99  " Prevent all folds from closing after 1st interaction

" Persistent undo
if !isdirectory("/tmp/vim-undo")
    call mkdir("/tmp/vim-undo", "", 0700)
endif
set undodir=/tmp/vim-undo
set undofile

" Comment plugin
packadd! comment  " `gcc` to toggle comment on current line

" File finding
set path+=**  " Search under every subdir under the current location

" Better prose editing for certain file types
augroup text_wrap
  autocmd!
  autocmd FileType markdown,text,gitcommit setlocal wrap linebreak breakindent
  autocmd FileType markdown,text,gitcommit nnoremap <buffer> j gj
  autocmd FileType markdown,text,gitcommit nnoremap <buffer> k gk
augroup END
