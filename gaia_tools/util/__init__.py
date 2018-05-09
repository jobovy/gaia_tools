import os, os.path
import tempfile
import shutil
import pickle

def save_pickles(savefilename,*args,**kwargs):
    """
    NAME:
       save_pickles
    PURPOSE:
       relatively safely save things to a pickle
    INPUT:
       savefilename - name of the file to save to; actual save operation will be performed on a temporary file and then that file will be shell mv'ed to savefilename
       +things to pickle (as many as you want!)
    OUTPUT:
       none
    HISTORY:
       2010-? - Written - Bovy (NYU)
       2011-08-23 - generalized and added to galpy.util - Bovy (NYU)
       2018-05-04 - Copied from galpy into gaia_tools - Bovy (UofT)
    """
    saving= True
    interrupted= False
    file, tmp_savefilename= tempfile.mkstemp() #savefilename+'.tmp'
    os.close(file) #Easier this way
    while saving:
        try:
            savefile= open(tmp_savefilename,'wb')
            file_open= True
            for f in args:
                pickle.dump(f,savefile,pickle.HIGHEST_PROTOCOL)
            savefile.close()
            file_open= False
            shutil.move(tmp_savefilename,savefilename)
            saving= False
            if interrupted:
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            if not saving:
                raise
            print("KeyboardInterrupt ignored while saving pickle ...")
            interrupted= True
        finally:
            if file_open:
                savefile.close()
