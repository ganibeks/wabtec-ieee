function write_json(file,value)
fid=fopen(file,'w'); assert(fid>=0,'Cannot write %s',file);
c=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,PrettyPrint=true));
end
