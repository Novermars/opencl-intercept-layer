
R"===(

# Copyright (c) 2023 Intel Corporation
#
# SPDX-License-Identifier: MIT

import numpy as np
import pyopencl as cl
import glob as gl
import re
import hashlib
import struct
import os

buffer_idx = []
input_buffers = {}
output_buffers = {}
buffer_files = gl.glob("./Buffer*.bin")
for buffer in buffer_files:
    idx = int(re.findall(r'\d+', buffer)[0])
    buffer_idx.append(idx)
    input_buffers[idx] = np.fromfile(buffer, dtype='uint8').tobytes()
    output_buffers[idx] = np.empty_like(input_buffers[idx])

arguments = {}
argument_files = gl.glob("./Argument*.bin")
for argument in argument_files:
    idx = int(re.findall(r'\d+', argument)[0])
    arguments[idx] = np.fromfile(argument, dtype='uint8').tobytes()

# Make sure that we only set the arguments to the non-buffer parameters
for idx in list(input_buffers):
    del arguments[idx]

ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)
devices = ctx.get_info(cl.context_info.DEVICES)

mf = cl.mem_flags

gpu_buffers = {}
for idx in buffer_idx:
    gpu_buffers[idx] = cl.Buffer(ctx, mf.COPY_HOST_PTR, hostbuf=input_buffers[idx])

with open("buildOptions.txt", 'r') as file:
    flags = [line.rstrip() for line in file]
    print(f"Using flags: {flags}")

if os.path.isfile("kernel.cl"):
    with open("kernel.cl", 'r') as file:
        kernel = file.read()
    prg = cl.Program(ctx, kernel).build(flags)
else:
    binary_files = gl.glob("./binary_*")
    binaries = []
    for file in binary_files:
        binaries.append(np.fromfile(file, dtype='uint8').tobytes())

    # Try the binaries to find one that works
    for idx in range(len(binaries)):
        try:
            prg = cl.Program(ctx, [devices[0]], binaries[idx]).build(flags)
            break
        except:
            pass

with open('knlName.txt') as file:
        knl_name = file.read()
knl = getattr(prg, knl_name)
for pos, argument in arguments.items():
    knl.set_arg(pos, argument)

for pos, buffer in gpu_buffers.items():
    knl.set_arg(pos, buffer)

with open("worksizes.txt", 'r') as file:
    lines = [line.rstrip() for line in file]

gws = []
lws = []
gws_offset = []

for idx in range(3):
    gws.append(int(lines[3 * idx + 0]))
    lws.append(int(lines[3 * idx + 1]))
    gws_offset.append(int(lines[3 * idx + 2]))
    
print(f"Global Worksize: {gws}")
print(f"Local Worksize: {lws}")
print(f"Global Worksize Offsets: {gws_offset}")
    
if lws == [0, 0, 0]:
    lws = None
    
cl.enqueue_nd_range_kernel(queue, knl, gws, lws, gws_offset)

for pos in gpu_buffers.keys():
    cl.enqueue_copy(queue, output_buffers[pos], gpu_buffers[pos])

for pos, cpu_buffer in output_buffers.items():
    cpu_buffer.tofile("output_buffer" + str(pos) + ".bin")
)==="
