"""List of intrinsic Fortran functions.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
# This is a mash of standard and GFortran intrinsics.
# Maybe someday I'll try to sort them out.

intrinsic_fns = [
    'abort',
    'abs',
    'access',
    'achar',
    'acos',
    'acosd',
    'acosh',
    'adjustl',
    'adjustr',
    'aimag',
    'aint',
    'alarm',
    'all',
    'allocated',
    'and',
    'anint',
    'any',
    'asin',
    'asind',
    'asinh',
    'associated',
    'atan',
    'atand',
    'atan2',
    'atan2d',
    'atanh',
    'atomic_add',
    'atomic_and',
    'atomic_cas',
    'atomic_define',
    'atomic_fetch_add',
    'atomic_fetch_and',
    'atomic_fetch_or',
    'atomic_fetch_xor',
    'atomic_or',
    'atomic_ref',
    'atomic_xor',
    'backtrace',
    'bessel_j0',
    'bessel_j1',
    'bessel_jn',
    'bessel_y0',
    'bessel_y1',
    'bessel_yn',
    'bge',
    'bgt',
    'bit_size',
    'ble',
    'blt',
    'btest',
    'c_associated',
    'c_f_pointer',
    'c_f_procpointer',
    'c_funloc',
    'c_loc',
    'c_sizeof',
    'ceiling',
    'char',
    'chdir',
    'chmod',
    'cmplx',
    'co_broadcast',
    'co_max',
    'co_min',
    'co_reduce',
    'co_sum',
    'command_argument_count',
    'compiler_options',
    'compiler_version',
    'complex',
    'conjg',
    'cos',
    'cosd',
    'cosh',
    'cotan',
    'cotand',
    'count',
    'cpu_time',
    'cshift',
    'ctime',
    'date_and_time',
    'dble',
    'dcmplx',
    'digits',
    'dim',
    'dot_product',
    'dprod',
    'dreal',
    'dshiftl',
    'dshiftr',
    'dtime',
    'eoshift',
    'epsilon',
    'erf',
    'erfc',
    'erfc_scaled',
    'etime',
    'event_query',
    'execute_command_line',
    'exit',
    'exp',
    'exponent',
    'extends_type_of',
    'fdate',
    'fget',
    'fgetc',
    'findloc',
    'floor',
    'flush',
    'fnum',
    'fput',
    'fputc',
    'fraction',
    'free',
    'fseek',
    'fstat',
    'ftell',
    'gamma',
    'gerror',
    'getarg',
    'get_command',
    'get_command_argument',
    'getcwd',
    'getenv',
    'get_environment_variable',
    'getgid',
    'getlog',
    'getpid',
    'getuid',
    'gmtime',
    'hostnm',
    'huge',
    'hypot',
    'iachar',
    'iall',
    'iand',
    'iany',
    'iargc',
    'ibclr',
    'ibits',
    'ibset',
    'ichar',
    'idate',
    'ieor',
    'ierrno',
    'image_index',
    'index',
    'int',
    'int2',
    'int8',
    'ior',
    'iparity',
    'irand',
    'is_contiguous',
    'is_iostat_end',
    'is_iostat_eor',
    'isatty',
    'ishft',
    'ishftc',
    'isnan',
    'itime',
    'kill',
    'kind',
    'lbound',
    'lcobound',
    'leadz',
    'len',
    'len_trim',
    'lge',
    'lgt',
    'link',
    'lle',
    'llt',
    'lnblnk',
    'loc',
    'log',
    'log10',
    'log_gamma',
    'logical',
    'long',
    'lshift',
    'lstat',
    'ltime',
    'malloc',
    'maskl',
    'maskr',
    'matmul',
    'max',
    'maxexponent',
    'maxloc',
    'maxval',
    'mclock',
    'mclock8',
    'merge',
    'merge_bits',
    'min',
    'minexponent',
    'minloc',
    'minval',
    'mod',
    'modulo',
    'move_alloc',
    'mvbits',
    'nearest',
    'new_line',
    'nint',
    'norm2',
    'not',
    'null',
    'num_images',
    'or',
    'pack',
    'parity',
    'perror',
    'popcnt',
    'poppar',
    'precision',
    'present',
    'product',
    'radix',
    'ran',
    'rand',
    'random_init',
    'random_number',
    'random_seed',
    'range',
    'rank ',
    'real',
    'rename',
    'repeat',
    'reshape',
    'rrspacing',
    'rshift',
    'same_type_as',
    'scale',
    'scan',
    'secnds',
    'second',
    'selected_char_kind',
    'selected_int_kind',
    'selected_real_kind',
    'set_exponent',
    'shape',
    'shifta',
    'shiftl',
    'shiftr',
    'sign',
    'signal',
    'sin',
    'sind',
    'sinh',
    'size',
    'sizeof',
    'sleep',
    'spacing',
    'spread',
    'sqrt',
    'srand',
    'stat',
    'storage_size',
    'sum',
    'symlnk',
    'system',
    'system_clock',
    'tan',
    'tand',
    'tanh',
    'this_image',
    'time',
    'time8',
    'tiny',
    'trailz',
    'transfer',
    'transpose',
    'trim',
    'ttynam',
    'ubound',
    'ucobound',
    'umask',
    'unlink',
    'unpack',
    'verify',
    'xor',
] + [
    # Operators?  What are these called?
    'allocate',
    'deallocate',
]
