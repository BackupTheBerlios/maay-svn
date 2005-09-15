import sys
import os
import stat

def nsis_install(prefix, directory):
	print '  SetOutPath "%s"' % os.path.join('$INSTDIR', directory[len(prefix) + 1:])
	filenames = os.listdir(directory)
	directories = []
	for fn in filenames:
		absolute_filename = os.path.join(directory, fn)
		mode = os.lstat(absolute_filename)[stat.ST_MODE]
		if stat.S_ISDIR(mode):
			directories.append(os.path.join(directory, fn))
		else:
			print '  File "%s"' % os.path.join(directory, fn)

	for d in directories:
		nsis_install(prefix, d)

def nsis_remove(prefix, directory):
	filenames = os.listdir(directory)
	files = []
	for fn in filenames:
		absolute_filename = os.path.join(directory, fn)
		mode = os.lstat(absolute_filename)[stat.ST_MODE]
		if stat.S_ISDIR(mode):
			nsis_remove(prefix, os.path.join(directory, fn))
		else:
			files.append('%s' % os.path.join('$INSTDIR', directory[len(prefix) + 1:], fn))
	for f in files:
		print '  Delete "%s"' % f
	print '  RMDir "%s"' % os.path.join('$INSTDIR', directory[len(prefix) + 1:])



if sys.argv[1] == 'install':
	nsis_install(prefix=sys.argv[2], directory=sys.argv[2])
elif sys.argv[1] == 'uninstall':
	nsis_remove(prefix=sys.argv[2], directory=sys.argv[2])
	