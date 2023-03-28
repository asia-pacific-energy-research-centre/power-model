
#%%
#remove the following from the yaml file config/environment.yml
bad_lines= ['harfbuzz=6.0.0=he256f1b_0','libogg=1.3.4=h8ffe710_1','liblapack=3.9.0=16_win64_mkl','libxml2=2.10.3=hc3477c8_0','m2w64-gcc-libgfortran=5.3.0=6','expat=2.5.0=h1537add_0','xorg-kbproto=1.0.7=hcd874cb_1002','pywinpty=2.0.10=py39h99910a6_0','mkl=2022.1.0=h6a75c08_874','libhwloc=2.9.0=h51c2c0f_0','xorg-libxdmcp=1.1.3=hcd874cb_0','m2w64-libwinpthread-git=5.0.0.4634.697f757=2','libcblas=3.9.0=16_win64_mkl','pixman=0.40.0=h8ffe710_0','fribidi=1.0.10=h8d14728_0','gts=0.7.6=h7c369d9_2','zeromq=4.3.4=h0e60522_1','libglib=2.74.1=he8f3873_1','python=3.9.15=h4de0772_0_cpython','gstreamer=1.22.0=h6b5321d_2','tornado=6.2=py39ha55989b_1','pyqt5-sip=12.11.0=py39h99910a6_3','jpeg=9e=hcfcfb64_3','xorg-libxext=1.3.4=hcd874cb_2','m2w64-gcc-libs-core=5.3.0=7','jupyter_core=5.2.0=py39hcbf5309_0','glib-tools=2.74.1=h12be248_1','terminado=0.15.0=py39hcbf5309_0','zstd=1.5.2=h12be248_6','pydot=1.4.2=py39hcbf5309_3','libxcb=1.13=hcd874cb_1004','pyzmq=25.0.0=py39hea35a22_0','intel-openmp=2023.0.0=h57928b3_25922','jupyter=1.0.0=py39hcbf5309_8','numpy=1.23.5=py39hbccbffa_0','glib=2.74.1=h12be248_1','libsodium=1.0.18=h8d14728_1','libzlib=1.2.13=hcfcfb64_4','xorg-libx11=1.8.4=hcd874cb_0','icu=70.1=h0e60522_0','msys2-conda-epoch=20160418=1','vs2015_runtime=14.34.31931=h4c5c07a_10','debugpy=1.6.6=py39h99910a6_0','pthreads-win32=2.9.1=hfa6e2cd_3','xorg-xproto=7.0.31=hcd874cb_1007','libsqlite=3.40.0=hcfcfb64_0','xorg-libxpm=3.5.13=hcd874cb_0','pywin32=304=py39h99910a6_2','xorg-libxau=1.0.9=hcd874cb_0','libblas=3.9.0=16_win64_mkl','markupsafe=2.1.2=py39ha55989b_0','pandoc=2.19.2=h57928b3_1','pyqt=5.15.7=py39hb77abff_3','glpk=4.65=h2bbff1b_3','ucrt=10.0.22621.0=h57928b3_0','krb5=1.20.1=heb0366b_0','freetype=2.12.1=h546665d_1','psutil=5.9.4=py39ha55989b_0','tk=8.6.12=h8ffe710_0','argon2-cffi-bindings=21.2.0=py39ha55989b_3','gettext=0.21.1=h5728263_0','zlib=1.2.13=hcfcfb64_4','cffi=1.15.1=py39h68f70e3_3','libgd=2.3.3=hf5a96e7_4','libclang13=15.0.7=default_h77d9078_1','libwebp-base=1.2.4=h8ffe710_0','vc=14.3=hb6edc58_10','libpng=1.6.39=h19919ed_0','libdeflate=1.17=hcfcfb64_0','sip=6.7.7=py39h99910a6_0','yaml=0.2.5=h8ffe710_2','fontconfig=2.14.2=hbde0cde_0','openssl=3.0.8=hcfcfb64_0','winpty=0.4.3=4','gst-plugins-base=1.22.0=h001b923_2','libwebp=1.2.4=hcfcfb64_1','xorg-xextproto=7.3.0=hcd874cb_1003','cairo=1.16.0=hd694305_1014','lerc=4.0.0=h63175ca_0','bzip2=1.0.8=h8ffe710_4','libvorbis=1.3.7=h0e60522_0','libiconv=1.17=h8ffe710_0','libclang=15.0.7=default_h77d9078_1','getopt-win32=0.1=h8ffe710_0','m2w64-gcc-libs=5.3.0=7','pandas=1.5.2=py39h2ba5b7c_0','libffi=3.4.2=h8ffe710_5','libtiff=4.5.0=hf8721a0_2','graphviz=7.1.0=h51cb2cd_0','qt-main=5.15.8=h720456b_6','xorg-libxt=1.2.1=hcd874cb_2','pyyaml=6.0=py39ha55989b_5','tbb=2021.8.0=h91493d7_0','pango=1.50.13=hdffb7b3_0','xorg-libice=1.0.10=hcd874cb_0','pthread-stubs=0.4=hcd874cb_1001','xorg-libsm=1.2.3=hcd874cb_1000','m2w64-gmp=6.1.0=2','graphite2=1.3.13=1000','ca-certificates=2023.01.10=haa95532_0','xz=5.2.6=h8d14728_0','pcre2=10.40=h17e33f8_0']
#%%
#load ytaml

import yaml
with open('../config/environment.yml', 'r') as f:
    env = yaml.safe_load(f)
    print(env)
#%%
#remove lines in bad lines from dependencies key in env
i = 0
for line in env['dependencies']:
    #if line in bad_lines remove line
    # if line is a string then check it, else see if it is a list/dict/set and check each element
    if isinstance(line, str):
        if line in bad_lines:
            env['dependencies'].remove(line)
            print('removed line: ',line)
            i+=1
    elif isinstance(line, list):
        for subline in line:
            if subline in bad_lines:
                env['dependencies'].remove(line)
                print('removed line: ',line)
                i+=1
    elif isinstance(line, dict):
        for subline in line.values():
            if subline in bad_lines:
                env['dependencies'].remove(line)
                print('removed line: ',line)
                i+=1
    elif isinstance(line, set):
        for subline in line:
            if subline in bad_lines:
                env['dependencies'].remove(line)
                print('removed line: ',line)
                i+=1
    else:
        print('line is not a string, list, dict or set')
        print('line = ',line)
#check that i = len(bad_lines)
print('i = ',i)
print('len(bad_lines) = ',len(bad_lines))

#%%
print([key for key in env.keys()])
