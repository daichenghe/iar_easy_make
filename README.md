# IAR_EASY_MAKE

## 编译配置文件

本项目为IAR交叉编译，可将IAR添加至环境变量PATH中，或指定IAR编译器路径，配置在.ini文件中：

```
[default]
flag=--endian=little --cpu=Cortex-M7 --fpu=VFPv5_D16 --debug -Ohs --no_size_constraints -e  
cpu= 8
gcc = iccarm.exe
ar = iarchive.exe
tc_link= ilinkarm.exe
```

工程信息配置在.mk文件中：
```
; 目标格式：lib, bin等，暂只支持输出library文件
mode: exe

; 源文件
src:	./src/ephemeris.c
src:	./src/gnss_filter.c
src:	./src/gnss_integrity.c

; 中间文件路径
int: objs

; 输出文件
out: objs/gnss_lib
```
