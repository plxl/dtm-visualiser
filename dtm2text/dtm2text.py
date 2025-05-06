import sys
import argparse
import os.path
import struct
from io import BytesIO
from pathlib import Path


def byte_inputs_from_file(movie):
    "Generate input data from DTM movie."
    input_bytes = 8
    while True:
        input_data = movie.read(input_bytes)
        if not input_data:
            break
        yield input_data


def text_input_from_bytes(input_data):
    "Convert DTM input data to text."
    flags, l, r, a_x, a_y, c_x, c_y = struct.unpack("H6B", input_data)
    start_flag = flags & 1
    a_flag = flags >> 1 & 1
    b_flag = flags >> 2 & 1
    x_flag = flags >> 3 & 1
    y_flag = flags >> 4 & 1
    z_flag = flags >> 5 & 1
    d_up = flags >> 6 & 1
    d_down = flags >> 7 & 1
    d_left = flags >> 8 & 1
    d_right = flags >> 9 & 1
    l_flag = flags >> 10 & 1
    r_flag = flags >> 11 & 1
    button_data = (start_flag, a_flag, b_flag, x_flag, y_flag,
                   z_flag, d_up, d_down, d_left, d_right, l_flag,
                   r_flag, l, r, a_x, a_y, c_x, c_y)
    return ":".join(str(b) for b in button_data)


def byte_input_from_text(input_data):
    "Convert text input data to DTM."
    if input_data == '\n':
        result = b''
    elif input_data[0] == '#':
        result = b''
    else:
        start_flag, a_flag, b_flag, x_flag, y_flag, z_flag, d_up, d_down, d_left, d_right, l_flag, r_flag, l, r, a_x, a_y, c_x, c_y = (int(b) for b in input_data.split(":"))
        flags = r_flag
        flags = flags << 1 | l_flag
        flags = flags << 1 | d_right
        flags = flags << 1 | d_left
        flags = flags << 1 | d_down
        flags = flags << 1 | d_up
        flags = flags << 1 | z_flag
        flags = flags << 1 | y_flag
        flags = flags << 1 | x_flag
        flags = flags << 1 | b_flag
        flags = flags << 1 | a_flag
        flags = flags << 1 | start_flag
        result = struct.pack("H6B", flags, l, r, a_x, a_y, c_x, c_y)
    return result


def text2dtm(argv=None):
    if argv is None:
        argv = sys.argv

    description = ('Convert header + plain text input data to DTM.')
    parser = argparse.ArgumentParser(description=description,
                                     fromfile_prefix_chars='@')
    parser.add_argument('output', help='output file name')
    parser.add_argument('header', help='256 byte header file')
    parser.add_argument('infile', nargs='?', default='-',
                        help='file of inputs, one per line;'
                        ' if none provided, defaults to stdin')

    args = parser.parse_args(argv[1:])

    movie_path = args.output
    header_path = args.header
    input_path = args.infile

    i = 0
    movie_data = BytesIO()

    with open(header_path, mode='rb') as bin_header_file:
        movie_data.write(bin_header_file.read())

    with open(input_path, mode='r') if input_path != '-' else sys.stdin as text_input_file:
        for text_input in text_input_file:
            byte_input = byte_input_from_text(text_input)
            if byte_input:
                i += 1
                movie_data.write(byte_input)

    movie_view = movie_data.getbuffer()
    movie_view[13:21] = struct.pack("Q", i // 2)  # trick the frame data
    movie_view[21:29] = struct.pack("Q", i)  # set the input count
    movie_view[237:245] = struct.pack("Q", i * 2125000)  # trick the tick count

    with open(movie_path, mode='wb') as bin_movie_file:
        bin_movie_file.write(movie_data.getvalue())

    return 0


def dtm2text(argv=None):
    if argv is None:
        argv = sys.argv

    description = ('Convert DTM to header file + plain text input data.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('movie', help='the DTM to dump')
    parser.add_argument('-o', '--output', default='', metavar='DIR', help='the output directory')
    parser.add_argument('--no-header', action='store_true', help='only output the inputs.txt')

    args = parser.parse_args(argv[1:])

    movie_path = args.movie
    movie_basename = os.path.basename(movie_path)
    header_bytes = 256
    
    output_dir = Path(__file__).resolve().parent
    output_path = Path(args.output) if args.output else None
    
    if output_path and not output_path.exists():
        print(f'error: output directory does not exist: {args.output}')
        return
    
    output_dir = output_path or output_dir
    
    header_path = output_dir / f"{movie_basename}_header"
    input_path = output_dir / f"{movie_basename}_inputs.txt"

    with open(movie_path, mode='rb') as bin_movie_file:
        # This has the side effect of advancing the movie file.
        # That's a good thing in our case.
        header_bytes = bin_movie_file.read(header_bytes)

        if not args.no_header:
            with open(header_path, mode='wb') as bin_header_file:
                bin_header_file.write(header_bytes)

        with open(input_path, mode='w') as text_input_file:
            for byte_input in byte_inputs_from_file(bin_movie_file):
                text_input = text_input_from_bytes(byte_input)
                text_input_file.write(text_input + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(dtm2text())
