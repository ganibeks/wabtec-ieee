function h = add(m,src,name,pos,varargin)
h=add_block(src,[m '/' name],'Position',pos);
if ~isempty(varargin), set_param(h,varargin{:}); end
end
