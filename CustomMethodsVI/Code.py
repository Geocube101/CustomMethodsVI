from __future__ import annotations

import cv2
import enum
import itertools
import PIL.Image
import PIL.ImageDraw
import math
import numpy
import typing
import zlib

from . import Exceptions
from . import Math
from . import Misc
from . import Stream


class CodeDecodeFailure(RuntimeError):
	pass


class QRCode:
	pass


class Barcode:
	pass


class PixelCode:
	"""
	Class allowing encoding and decoding for custom multicolor pixel-codes
	"""

	__VERSION_HEADER: int = 8
	__SQUARE_SIZE: int = 96
	__DECODE_SIZE: tuple[int, int] = (__SQUARE_SIZE - 8, __SQUARE_SIZE - 20)

	# ECC: 800 + 520
	class CodeMask(enum.IntFlag):
		NONE: int = 0b0000

		XOR_1: int = 0b0001
		XOR_2: int = 0b0010
		XOR_3: int = 0b0100
		XOR_4: int = 0b1000

	@staticmethod
	def __get_image_alignment_nodes__(image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]]) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
		def quadrangle_area(quadrangle: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]) -> float:
			p1, p2, p3, p4 = tuple(Math.Vector.Vector(x) for x in sorted(quadrangle, key=lambda v: (Math.Vector.Vector(v) - center).length_squared()))
			d1: Math.Vector.Vector = p3 - p2
			d2: Math.Vector.Vector = p4 - p1
			return d1.length() * d2.length() / 2

		image = image // 128 * 255
		hsv: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
		grayscale: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
		grayscale = cv2.convertScaleAbs(grayscale, alpha=5)
		_, thresh = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
		square_points: list[tuple[int, int]] = []
		nodes: list[numpy.ndarray] = []
		node_center: Math.Vector.Vector = Math.Vector.Vector(0, 0)
		alignment = image.copy()

		if len(contours) < 4:
			raise CodeDecodeFailure('Failed to decode pixel-code image\n ...\nFailed to locate image contours')

		for i, contour in enumerate(contours):
			parent: numpy.ndarray = hierarchy[0, i, 3]
			parent2: numpy.ndarray = -1 if parent == -1 else hierarchy[0, parent, 3]
			parent3: numpy.ndarray = -1 if parent2 == -1 else hierarchy[0, parent2, 3]

			if parent == -1 or parent2 == -1 or parent3 != -1:
				continue

			moments: dict[str, float] = cv2.moments(contour)
			zero: float = moments['m00']
			cx: int = 0 if zero == 0 else round(int(moments['m10'] / zero))
			cy: int = 0 if zero == 0 else round(int(moments['m01'] / zero))
			h, s, v, *_ = hsv[cy, cx, :]

			if v > 16:
				continue

			nodes.append(contours[parent])
			node_center += Math.Vector.Vector(cx, cy)

		node_center /= len(nodes)

		for i, contour in enumerate(nodes):
			x, y, w, h = cv2.boundingRect(contour)
			p1: Math.Vector.Vector = Math.Vector.Vector(x, y)
			p2: Math.Vector.Vector = Math.Vector.Vector(x + w, y)
			p3: Math.Vector.Vector = Math.Vector.Vector(x, y + h)
			p4: Math.Vector.Vector = Math.Vector.Vector(x + w, y + h)
			farthest: Math.Vector.Vector = max((p1, p2, p3, p4), key=lambda v: (v - node_center).length_squared())
			cx, cy = farthest
			square_points.append((round(cx), round(cy)))

		#cv2.drawContours(alignment, contours, -1, (255, 255, 0), 1)
		#cv2.imshow('Contours', alignment)
		#cv2.waitKey()

		my, mx, *_ = image.shape
		center: Math.Vector.Vector = Math.Vector.Vector(image.shape[0] / 100 * 5, image.shape[1] / 100 * 15)
		quadrangles: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]] = list(itertools.combinations(((cx, cy) for cx, cy in square_points), 4))
		del quadrangles[256:]
		quadrangles.sort(key=quadrangle_area, reverse=True)
		square_points: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]] = quadrangles[0]

		if len(square_points) != 4:
			raise CodeDecodeFailure('Failed to decode pixel-code image\n ...\nFailed to locate pixel-code alignment nodes')

		n1, n2, n3, n4 = square_points
		return n4, n2, n3, n1

	@staticmethod
	def __encode_version_0__(image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]], mask: int, header: bytes, payload: bytes) -> PIL.Image.Image:
		"""
		Encodes the data using pixel-code version 0
		:param image: The image to write to
		:param mask: The masking type to use
		:param header: The header bytes to write
		:param payload: The data to write
		:return: The written image
		"""

		max_index: int = PixelCode.__SQUARE_SIZE - 1
		zx, zy = max_index - 4, max_index - 10
		position: list[int] = [zx, zy]
		groupdex: int = 0
		color_offset: int = 0
		colors: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]] = ((0xFF, 0xFF, 0xFF), (0xFF, 0x00, 0x00), (0x00, 0xFF, 0x00), (0x00, 0x00, 0xFF))
		version_index: int = math.ceil(PixelCode.__VERSION_HEADER / 2)

		content: Stream.BitStream = Stream.BitStream()
		content.write_padded(0, PixelCode.__VERSION_HEADER)
		content.write_padded(mask, 4)
		content.write_padded(header, 16)
		content.write_padded(payload, PixelCode.version_size(0) * 8 + 12)

		for packet in content.read():
			if position[0] == 3:
				raise OverflowError('Too many bits to encode')

			for i in range(4):
				bits: int = (packet & 0b11000000) >> 6
				packet <<= 2

				if groupdex >= 2 + version_index:
					if (mask & PixelCode.CodeMask.XOR_1) != 0 and groupdex % 3 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_2) != 0 and groupdex % 5 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_3) != 0 and groupdex % 7 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_4) != 0 and groupdex % 11 == 0:
						bits ^= groupdex & 0b11

				color: tuple[int, int, int] = colors[(bits + color_offset) % len(colors)]
				groupdex += 1
				image[position[1], position[0], :] = color
				position[1] -= 1

				if position[1] == 9:
					position[1] = zy
					position[0] -= 1

					if position[0] == 3:
						break

		padded: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.full((PixelCode.__SQUARE_SIZE + 16, PixelCode.__SQUARE_SIZE + 16, 3), 0xFF, dtype=numpy.uint8)
		padded[8:8 + PixelCode.__SQUARE_SIZE, 8:8 + PixelCode.__SQUARE_SIZE, :] = image
		return PIL.Image.fromarray(padded)

	@staticmethod
	def __encode_version_1__(image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]], mask: int, header: bytes, payload: bytes) -> PIL.Image.Image:
		"""
		Encodes the data using pixel-code version 1
		:param image: The image to write to
		:param mask: The masking type to use
		:param header: The header bytes to write
		:param payload: The data to write
		:return: The written image
		"""

		max_index: int = PixelCode.__SQUARE_SIZE - 1
		zx, zy = max_index - 4, max_index - 10
		position: list[int] = [zx, zy]
		groupdex: int = 0
		color_offset: int = 0
		colors: tuple[tuple[int, int, int], ...] = ((0xFF, 0xFF, 0xFF), (0xFF, 0x00, 0x00), (0x00, 0xFF, 0x00), (0x00, 0x00, 0xFF), (0xFF, 0xFF, 0x00), (0xFF, 0x00, 0xFF), (0x00, 0xFF, 0xFF), (0x00, 0x00, 0x00))
		version_index: int = math.ceil(PixelCode.__VERSION_HEADER / 2)

		content: Stream.BitStream = Stream.BitStream()
		content.write_padded(1, PixelCode.__VERSION_HEADER)
		content.write_padded(mask, 6)
		content.write_padded(header, 16)
		content.write_padded(payload, PixelCode.version_size(1) * 8 + 14)

		for i in range(version_index):
			bits: int = content.read(2)[0]
			groupdex += 1
			color: tuple[int, int, int] = colors[(bits + color_offset) % len(colors)]
			image[position[1], position[0], :] = color
			position[1] -= 1

			if position[1] == 9:
				position[1] = zy
				position[0] -= 1

				if position[0] == 3:
					raise OverflowError('Too many bits to encode')

		while not content.empty():
			bits: int = content.read(3)[0]

			if position[0] == 3:
				raise OverflowError('Too many bits to encode')

			if groupdex >= version_index + 2:
				if (mask & PixelCode.CodeMask.XOR_1) != 0 and groupdex % 3 == 0:
					bits ^= groupdex & 0b111
				if (mask & PixelCode.CodeMask.XOR_2) != 0 and groupdex % 5 == 0:
					bits ^= groupdex & 0b111
				if (mask & PixelCode.CodeMask.XOR_3) != 0 and groupdex % 7 == 0:
					bits ^= groupdex & 0b111
				if (mask & PixelCode.CodeMask.XOR_4) != 0 and groupdex % 11 == 0:
					bits ^= groupdex & 0b111

			color: tuple[int, int, int] = colors[(bits + color_offset) % len(colors)]
			groupdex += 1
			image[position[1], position[0], :] = color
			position[1] -= 1

			if position[1] == 9:
				position[1] = zy
				position[0] -= 1

		padded: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.full((PixelCode.__SQUARE_SIZE + 16, PixelCode.__SQUARE_SIZE + 16, 3), 0xFF, dtype=numpy.uint8)
		padded[8:8 + PixelCode.__SQUARE_SIZE, 8:8 + PixelCode.__SQUARE_SIZE, :] = image
		return PIL.Image.fromarray(padded)

	@staticmethod
	def __decode_version_0__(image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]], red: tuple[numpy.float64, numpy.float64, numpy.float64], green: tuple[numpy.float64, numpy.float64, numpy.float64], blue: tuple[numpy.float64, numpy.float64, numpy.float64], thresh: tuple[float, float, float], grid_position: tuple[float, float], grid_cell: float, scan_size: int) -> bytes:
		"""
		Decodes the image using pixel-code version 0
		:param image: The image to read
		:param red: The red hue, saturation, and value
		:param green: The green hue, saturation, and value
		:param blue: The blue hue, saturation, and value
		:param thresh: The hue, saturation, and value thresholds
		:param grid_position: The starting pixel to read the grid from
		:param grid_cell: The size of a grid cell
		:param scan_size: The scanning size to average pixels across
		:return: The decoded binary data
		"""

		hue_thresh, sat_thresh, val_thresh = thresh
		red_hue, red_sat, red_val = red
		green_hue, green_sat, green_val = green
		blue_hue, blue_sat, blue_val = blue
		groupdex: int = 0
		mask: int = 0
		content: Stream.BitStream = Stream.BitStream()
		zx, zy = grid_position
		grid_pos: list[float] = [zx, zy]
		version_index: int = math.ceil(PixelCode.__VERSION_HEADER / 2)

		# Read image
		for i in range(PixelCode.__DECODE_SIZE[0]):
			for j in range(PixelCode.__DECODE_SIZE[1]):
				x: int = round(grid_pos[0])
				y: int = round(grid_pos[1])
				region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[y - scan_size:y + scan_size, x - scan_size:x + scan_size, :]
				average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.float64]] = numpy.mean(region, axis=(0, 1))
				average = numpy.fmod(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)), (180, 256, 256))
				h, s, v = average
				bits: int

				if (abs(h - red_hue) / 180 <= hue_thresh or abs(h - (red_hue + 180)) / 180 <= hue_thresh) and abs(s - red_sat) / 255 <= sat_thresh and abs(v - red_val) / 255 <= val_thresh:
					bits = 0b01
				elif (abs(h - green_hue) / 180 <= hue_thresh or abs(h - (green_hue + 180)) / 180 <= hue_thresh) and abs(s - green_sat) / 255 <= sat_thresh and abs(v - green_val) / 255 <= val_thresh:
					bits = 0b10
				elif (abs(h - blue_hue) / 180 <= hue_thresh or (abs(h - (blue_hue + 180)) / 180 <= hue_thresh)) and abs(s - blue_sat) / 255 <= sat_thresh and abs(v - blue_val) / 255 <= val_thresh:
					bits = 0b11
				elif s / 255 <= sat_thresh and abs(v - 255) / 255 <= val_thresh:
					bits = 0b00
				else:
					print(f'HUE: {round(h / 180 * 360, 2)}, THRESH: {round(hue_thresh * 100, 2)}, RED: {round(red_hue / 180 * 360)}, GREEN: {round(green_hue / 180 * 360)}, BLUE: {round(blue_hue / 180 * 360)}')
					print(f'SAT: {round(s / 255 * 100, 2)}, THRESH: {round(sat_thresh * 100, 2)}, RED: {round(red_sat / 255 * 100, 2)}, GREEN: {round(green_sat / 255 * 100, 2)}, BLUE: {round(blue_sat / 255 * 100, 2)}')
					print(f'VAL: {round(v / 255 * 100, 2)}, THRESH: {round(val_thresh * 100, 2)}, RED: {round(red_val / 255 * 100, 2)}, GREEN: {round(green_val / 255 * 100, 2)}, BLUE: {round(blue_val / 255 * 100, 2)}')
					cv2.imshow('Region', cv2.resize(region, (512, 512)))
					cv2.imshow('Average', cv2.resize(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_HSV2BGR), (512, 512)))
					cv2.circle(image, (x, y), 3, (0xFF, 0xFF, 0x00), -1, cv2.FILLED)
					cv2.circle(image, (x, y), 10, (0x00, 0x00, 0x00), 3)
					cv2.imshow('Where', image)
					cv2.waitKey()
					raise CodeDecodeFailure('Failed to decode pixel-code')

				if groupdex == version_index:
					mask |= bits << 2
				elif groupdex == version_index + 1:
					mask |= bits
				elif groupdex >= version_index + 2:
					if (mask & PixelCode.CodeMask.XOR_1) != 0 and groupdex % 3 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_2) != 0 and groupdex % 5 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_3) != 0 and groupdex % 7 == 0:
						bits ^= groupdex & 0b11
					if (mask & PixelCode.CodeMask.XOR_4) != 0 and groupdex % 11 == 0:
						bits ^= groupdex & 0b11

					content.write_padded(bits, 2)
				cv2.circle(image, (x, y), 3, (0xFF, 0xFF, 0x00), -1, cv2.FILLED)
				groupdex += 1
				grid_pos[1] -= grid_cell

			grid_pos[1] = zy
			grid_pos[0] -= grid_cell

		# Decode binary data
		#cv2.imshow('Grid', image)
		#cv2.waitKey()
		header: int = int.from_bytes(content.read(16), 'big', signed=False)
		is_compressed: bool = bool((header >> 15) & 0b1)
		payload_length: int = header & 0b0111111111111111

		if payload_length == 0:
			return b''

		content.read(len(content) - payload_length * 8)
		data: bytes = content.read()
		return zlib.decompress(data) if is_compressed else data

	@staticmethod
	def __decode_version_1__(image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]], red: tuple[numpy.float64, numpy.float64, numpy.float64], green: tuple[numpy.float64, numpy.float64, numpy.float64], blue: tuple[numpy.float64, numpy.float64, numpy.float64], thresh: tuple[float, float, float], grid_position: tuple[float, float], grid_cell: float, scan_size: int) -> bytes:
		"""
		Decodes the image using pixel-code version 1
		:param image: The image to read
		:param red: The red hue, saturation, and value
		:param green: The green hue, saturation, and value
		:param blue: The blue hue, saturation, and value
		:param thresh: The hue, saturation, and value thresholds
		:param grid_position: The starting pixel to read the grid from
		:param grid_cell: The size of a grid cell
		:param scan_size: The scanning size to average pixels across
		:return: The decoded binary data
		"""

		hue_thresh, sat_thresh, val_thresh = thresh
		hue_thresh *= 0.5
		red_hue, red_sat, red_val = red
		green_hue, green_sat, green_val = green
		blue_hue, blue_sat, blue_val = blue
		groupdex: int = 0
		mask: int = 0
		content: Stream.BitStream = Stream.BitStream()
		zx, zy = grid_position
		grid_pos: list[float] = [zx, zy]
		version_index: int = math.ceil(PixelCode.__VERSION_HEADER / 2)

		# Secondary Colors
		yellow_hue: float = (min(red_hue, abs(red_hue - 180)) + green_hue) / 2
		yellow_sat: float = (red_sat + green_sat) / 2
		yellow_val: float = (red_val + green_val) / 2

		cyan_hue: float = (green_hue + blue_hue) / 2
		cyan_sat: float = (green_sat + blue_sat) / 2
		cyan_val: float = (green_val + blue_val) / 2

		magenta_hue: float = (min(red_hue, abs(red_hue - 180)) + blue_hue) / 2 + 90
		magenta_sat: float = (red_sat + blue_sat) / 2
		magenta_val: float = (red_val + blue_val) / 2

		# Read image
		for i in range(PixelCode.__DECODE_SIZE[0]):
			for j in range(PixelCode.__DECODE_SIZE[1]):
				x: int = round(grid_pos[0])
				y: int = round(grid_pos[1])
				region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[y - scan_size:y + scan_size, x - scan_size:x + scan_size, :]
				average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.float64]] = numpy.mean(region, axis=(0, 1))
				average = numpy.fmod(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)), (180, 256, 256))
				h, s, v = average
				bits: int

				if (abs(h - red_hue) / 180 <= hue_thresh or abs(h - (red_hue + 180)) / 180 <= hue_thresh) and abs(s - red_sat) / 255 <= sat_thresh and abs(v - red_val) / 255 <= val_thresh:
					bits = 0b001
				elif (abs(h - green_hue) / 180 <= hue_thresh or abs(h - (green_hue + 180)) / 180 <= hue_thresh) and abs(s - green_sat) / 255 <= sat_thresh and abs(v - green_val) / 255 <= val_thresh:
					bits = 0b010
				elif (abs(h - blue_hue) / 180 <= hue_thresh or (abs(h - (blue_hue + 180)) / 180 <= hue_thresh)) and abs(s - blue_sat) / 255 <= sat_thresh and abs(v - blue_val) / 255 <= val_thresh:
					bits = 0b011
				elif (abs(h - yellow_hue) / 180 <= hue_thresh or abs(h - (yellow_hue + 180)) / 180 <= hue_thresh) and abs(s - yellow_sat) / 255 <= sat_thresh and abs(v - yellow_val) / 255 <= val_thresh:
					bits = 0b100
				elif (abs(h - magenta_hue) / 180 <= hue_thresh or abs(h - (magenta_hue + 180)) / 180 <= hue_thresh) and abs(s - magenta_sat) / 255 <= sat_thresh and abs(v - magenta_val) / 255 <= val_thresh:
					bits = 0b101
				elif (abs(h - cyan_hue) / 180 <= hue_thresh or (abs(h - (cyan_hue + 180)) / 180 <= hue_thresh)) and abs(s - cyan_sat) / 255 <= sat_thresh and abs(v - cyan_val) / 255 <= val_thresh:
					bits = 0b110
				elif s / 255 <= sat_thresh and abs(v - 255) / 255 <= val_thresh:
					bits = 0b000
				elif v / 255 <= val_thresh:
					bits = 0b111
				else:
					print(f'HUE: {round(h / 180 * 360, 2)}, THRESH: {round(hue_thresh * 100, 2)}, RED: {round(red_hue / 180 * 360)}, GREEN: {round(green_hue / 180 * 360)}, BLUE: {round(blue_hue / 180 * 360)}')
					print(f'SAT: {round(s / 255 * 100, 2)}, THRESH: {round(sat_thresh * 100, 2)}, RED: {round(red_sat / 255 * 100, 2)}, GREEN: {round(green_sat / 255 * 100, 2)}, BLUE: {round(blue_sat / 255 * 100, 2)}')
					print(f'VAL: {round(v / 255 * 100, 2)}, THRESH: {round(val_thresh * 100, 2)}, RED: {round(red_val / 255 * 100, 2)}, GREEN: {round(green_val / 255 * 100, 2)}, BLUE: {round(blue_val / 255 * 100, 2)}')
					cv2.imshow('Region', cv2.resize(region, (512, 512)))
					cv2.imshow('Average', cv2.resize(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_HSV2BGR), (512, 512)))
					cv2.circle(image, (x, y), 3, (0xFF, 0xFF, 0x00), 0)
					cv2.imshow('Where', cv2.resize(image, (1024, 1024)))
					cv2.waitKey()
					raise CodeDecodeFailure('Failed to decode pixel-code')

				if groupdex == version_index:
					mask |= bits << 3
				elif groupdex == version_index + 1:
					mask |= bits
				elif groupdex >= version_index + 2:
					if (mask & PixelCode.CodeMask.XOR_1) != 0 and groupdex % 3 == 0:
						bits ^= groupdex & 0b111
					if (mask & PixelCode.CodeMask.XOR_2) != 0 and groupdex % 5 == 0:
						bits ^= groupdex & 0b111
					if (mask & PixelCode.CodeMask.XOR_3) != 0 and groupdex % 7 == 0:
						bits ^= groupdex & 0b111
					if (mask & PixelCode.CodeMask.XOR_4) != 0 and groupdex % 11 == 0:
						bits ^= groupdex & 0b111

					content.write_padded(bits, 3)

				groupdex += 1
				grid_pos[1] -= grid_cell

			grid_pos[1] = zy
			grid_pos[0] -= grid_cell

		# Decode binary data
		header: int = int.from_bytes(content.read(16), 'big', signed=False)
		#print(mask, header)
		is_compressed: bool = bool((header >> 15) & 0b1)
		payload_length: int = header & 0b0111111111111111

		if payload_length == 0:
			return b''

		content.read(len(content) - payload_length * 8)
		data: bytes = content.read()
		return zlib.decompress(data) if is_compressed else data

	@staticmethod
	def version_size(version: int) -> int:
		"""
		Calculates the maximum amount of data (in bytes) a specific pixel-code version can store
		:param version: The pixel-code version
		:return: The maximum number of bytes than can be encoded
		:raises InvalidArgumentException: If 'version' is not an integer
		"""

		Misc.raise_ifn(isinstance(version, int), Exceptions.InvalidArgumentException(PixelCode.version_size, 'version', type(version), (int,)))
		version_bits: int = math.ceil(PixelCode.__VERSION_HEADER / 2)
		area: int = PixelCode.__DECODE_SIZE[0] * PixelCode.__DECODE_SIZE[1] - version_bits

		if version == 0:
			return (area * 2 - 4 - 16 - PixelCode.__VERSION_HEADER) // 8
		elif version == 1:
			return (area * 3 - 6 - 16 - PixelCode.__VERSION_HEADER) // 8
		else:
			raise ValueError(f'Invalid pixel-code version \'{version}\'')

	@staticmethod
	def encode(data: bytes | bytearray, mask: PixelCode.CodeMask | int = 0b1111, *, version: int = 0) -> PIL.Image.Image:
		"""
		Encodes data into a new pixel-code image
		:param data: The binary data to encode
		:param mask: The binary masks to use (defaults to all)
		:param version: The pixel-code version
		:return: The pixel-code image
		:raises ValueError: If the amount of data exceeds the maximum allowed count
		"""

		Misc.raise_ifn(isinstance(data, (bytes, bytearray)), Exceptions.InvalidArgumentException(PixelCode.encode, 'data', type(data), (bytes, bytearray)))
		Misc.raise_ifn(isinstance(mask, (int,)), Exceptions.InvalidArgumentException(PixelCode.encode, 'mask', type(mask), (int,)))
		Misc.raise_ifn(isinstance(version, (int,)), Exceptions.InvalidArgumentException(PixelCode.encode, 'version', type(version), (int,)))
		Misc.raise_if((mask := int(mask)).bit_length() > 4, ValueError('Mask must be between 0 and 15'))
		Misc.raise_if((version := int(version)).bit_length() > PixelCode.__VERSION_HEADER, ValueError(f'Mask must be between 0 and {2 ** PixelCode.__VERSION_HEADER - 1}'))

		max_index: int = PixelCode.__SQUARE_SIZE - 1
		image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.full((PixelCode.__SQUARE_SIZE, PixelCode.__SQUARE_SIZE, 3), 0xFF, numpy.uint8)

		# Alignment
		cv2.rectangle(image, (0, 0), (7, 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (2, 2), (5, 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (3, 3), (4, 4), (0x00, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (max_index, 0), (max_index - 7, 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (max_index - 2, 2), (max_index - 5, 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (max_index - 3, 3), (max_index - 4, 4), (0x00, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (0, max_index), (7, max_index - 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (2, max_index - 2), (5, max_index - 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (3, max_index - 3), (4, max_index - 4), (0x00, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (max_index - 0, max_index - 0), (max_index - 7, max_index - 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (max_index - 2, max_index - 2), (max_index - 5, max_index - 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (max_index - 3, max_index - 3), (max_index - 4, max_index - 4), (0x00, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (max_index, 9), (max_index - 1, max_index - 9), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (14, max_index), (max_index - 9, max_index - 1), (0x00, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (0, 9), (1, 10), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (0, max_index - 9), (1, max_index - 10), (0x00, 0x00, 0x00), cv2.FILLED)

		# Calibration
		cv2.rectangle(image, (9, 0), (11, 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (9, 1), (11, 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (9, 2), (11, 4), (0xFF, 0x00, 0x00), cv2.FILLED)

		cv2.rectangle(image, (max_index - 9, 0), (max_index - 11, 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (max_index - 9, 1), (max_index - 11, 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (max_index - 9, 2), (max_index - 11, 4), (0x00, 0x00, 0xFF), cv2.FILLED)

		cv2.rectangle(image, (9, max_index - 0), (11, max_index - 7), (0x00, 0x00, 0x00), cv2.FILLED)
		cv2.rectangle(image, (9, max_index - 1), (11, max_index - 5), (0xFF, 0xFF, 0xFF), cv2.FILLED)
		cv2.rectangle(image, (9, max_index - 2), (11, max_index - 4), (0x00, 0xFF, 0x00), cv2.FILLED)

		# Header
		compressed: bytes = zlib.compress(data := bytes(data), zlib.Z_BEST_COMPRESSION)
		is_compressed: bool = len(compressed) < len(data)
		payload: bytes = compressed if is_compressed else data
		payload_length: int = len(payload)
		header: bytes = (payload_length & 0b0111111111111111 | (0b1000000000000000 if is_compressed else 0b0000000000000000)).to_bytes(2, 'big', signed=False)
		max_size: int = PixelCode.version_size(version)

		if payload_length > max_size:
			raise ValueError(f'Payload length exceeds maximum storable amount: {payload_length} > {max_size}')

		# Content
		if version == 0:
			return PixelCode.__encode_version_0__(image, mask, header, payload)
		elif version == 1:
			return PixelCode.__encode_version_1__(image, mask, header, payload)
		else:
			raise ValueError(f'Unrecognized version \'{version}\'')

	@staticmethod
	def decode(pixel_code_image: PIL.Image.Image, *, alignment_iterations: int = 4) -> bytes:
		"""
		Decodes binary data from a pixel-code image
		:param pixel_code_image: The pixel-code image
		:param alignment_iterations: The number of iterations to align image
		:return: The encoded binary data
		:raises CodeDecodeFailure: If pixel-code decode failed
		"""

		# Straighten Image
		image: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = cv2.cvtColor(numpy.array(pixel_code_image), cv2.COLOR_RGB2BGR)
		alignment_iterations = int(alignment_iterations)
		scale: float = 8
		reconstruct_size: int = 1024

		for i in range(alignment_iterations):
			n1, n2, n3, n4 = PixelCode.__get_image_alignment_nodes__(image)
			p1: Math.Vector.Vector = Math.Vector.Vector(n1) + Math.Vector.Vector(-1, -1) * scale
			p2: Math.Vector.Vector = Math.Vector.Vector(n2) + Math.Vector.Vector(-1, 1) * scale
			p3: Math.Vector.Vector = Math.Vector.Vector(n3) + Math.Vector.Vector(1, -1) * scale
			p4: Math.Vector.Vector = Math.Vector.Vector(n4) + Math.Vector.Vector(1, 1) * scale

			src_coords: numpy.ndarray = numpy.array((p1.components(), p2.components(), p3.components(), p4.components()), dtype=numpy.float32).reshape((4, 2))
			dst_coords: numpy.ndarray = numpy.array(((0, 0), (0, reconstruct_size), (reconstruct_size, 0), (reconstruct_size, reconstruct_size)), dtype=numpy.float32).reshape((4, 2))
			transform: numpy.ndarray = cv2.getPerspectiveTransform(src_coords, dst_coords)
			fixed: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = cv2.warpPerspective(image, transform, (reconstruct_size, reconstruct_size), borderValue=(0xFF, 0xFF, 0xFF))
			image = numpy.full((reconstruct_size + 64, reconstruct_size + 64, 3), 0xFF, dtype=numpy.uint8)
			image[32:-32, 32:-32, :] = fixed

		# Rotate image
		n1, n2, n3, n4 = PixelCode.__get_image_alignment_nodes__(image)
		bottom_side: Math.Vector.Vector = Math.Vector.Vector(*n4) - Math.Vector.Vector(*n2)
		left_side: Math.Vector.Vector = Math.Vector.Vector(*n4) - Math.Vector.Vector(*n3)
		sq1: float = bottom_side.length()
		sq2: float = left_side.length()
		lp1: Math.Vector.Vector = bottom_side / 4
		lp2: Math.Vector.Vector = left_side / 4
		realign: bool = False
		aligned: bool = False

		for _ in range(4):
			aligned = True
			side_cell_size: int = 2
			black_thresh: float = 0.25

			for i in range(3):
				x1, y1 = Math.Vector.Vector(n2) + lp1 * (i + 1)
				x2, y2 = Math.Vector.Vector(n3) + lp2 * (i + 1)
				x1: int = round(x1)
				y1: int = round(y1 - 10)
				x2: int = round(x2 - 10)
				y2: int = round(y2)

				region_1: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[y1 - side_cell_size:y1 + side_cell_size, x1 - side_cell_size:x1 + side_cell_size, :]
				region_2: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[y2 - side_cell_size:y2 + side_cell_size, x2 - side_cell_size:x2 + side_cell_size, :]
				average_1: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.mean(region_1, axis=(0, 1))
				average_2: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.mean(region_2, axis=(0, 1))
				h1, s1, v1 = cv2.cvtColor(average_1.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)).astype(numpy.float64)
				h2, s2, v2 = cv2.cvtColor(average_2.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)).astype(numpy.float64)

				#copy = image.copy()
				#cv2.circle(copy, (x1, y1), 3, (255, 255, 0), -1, cv2.FILLED)
				#cv2.circle(copy, (x2, y2), 3, (255, 255, 0), -1, cv2.FILLED)
				#cv2.imshow('Target', copy)
				#cv2.waitKey()

				if v1 / 255 > black_thresh or v2 / 255 > black_thresh:
					aligned = False
					break

			if aligned:
				break
			else:
				image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
				realign = True

		if not aligned:
			raise CodeDecodeFailure('Failed to align pixel-code')
		elif realign:
			for _ in range(int(alignment_iterations)):
				n1, n2, n3, n4 = PixelCode.__get_image_alignment_nodes__(image)
				p1: Math.Vector.Vector = Math.Vector.Vector(n1) + Math.Vector.Vector(-1, -1) * scale
				p2: Math.Vector.Vector = Math.Vector.Vector(n2) + Math.Vector.Vector(-1, 1) * scale
				p3: Math.Vector.Vector = Math.Vector.Vector(n3) + Math.Vector.Vector(1, -1) * scale
				p4: Math.Vector.Vector = Math.Vector.Vector(n4) + Math.Vector.Vector(1, 1) * scale

				src_coords: numpy.ndarray = numpy.array((p1.components(), p2.components(), p3.components(), p4.components()), dtype=numpy.float32).reshape((4, 2))
				dst_coords: numpy.ndarray = numpy.array(((0, 0), (0, reconstruct_size), (reconstruct_size, 0), (reconstruct_size, reconstruct_size)), dtype=numpy.float32).reshape((4, 2))
				transform: numpy.ndarray = cv2.getPerspectiveTransform(src_coords, dst_coords)
				fixed: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = cv2.warpPerspective(image, transform, (reconstruct_size, reconstruct_size))
				image = numpy.full((reconstruct_size + 64, reconstruct_size + 64, 3), 0xFF, dtype=numpy.uint8)
				image[32:-32, 32:-32, :] = fixed

			n1, n2, n3, n4 = PixelCode.__get_image_alignment_nodes__(image)
			bottom_side = Math.Vector.Vector(*n4) - Math.Vector.Vector(*n2)
			left_side = Math.Vector.Vector(*n4) - Math.Vector.Vector(*n3)
			sq1 = bottom_side.length()
			sq2 = left_side.length()

		# Get grid cell size
		image = image // 128
		highest: numpy.uint8 = numpy.max(image)
		scale: float = 255 / highest
		image = (image * scale).astype(numpy.uint8)
		#cv2.imshow('Corrected', image)
		#cv2.waitKey()
		square_size: int = round((sq1 + sq2) / 2)
		grid_cell: float = square_size / PixelCode.__SQUARE_SIZE
		cell_size: int = round(grid_cell / 2)
		scan_size: int = cell_size >> 2
		zy: float = grid_cell * (PixelCode.__SQUARE_SIZE - (10.75 - 4))
		zx: float = grid_cell * (PixelCode.__SQUARE_SIZE - (1.75 - 1))

		# Get averaged red HSV
		rx: int = round(n1[0] + grid_cell * 10.5)
		ry: int = round(n1[1] + grid_cell * 3.5)
		red_region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[ry - cell_size:ry + cell_size, rx - cell_size:rx + cell_size, :]
		red_average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.mean(red_region, axis=(0, 1))
		red_hue, red_sat, red_val = cv2.cvtColor(red_average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)).astype(numpy.float64)

		# Get averaged green HSV
		gx: int = round(n1[0] + grid_cell * 10.5)
		gy: int = round(n1[1] + grid_cell * (PixelCode.__SQUARE_SIZE - 4))
		green_region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[gy - cell_size:gy + cell_size, gx - cell_size:gx + cell_size, :]
		green_average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.mean(green_region, axis=(0, 1))
		green_hue, green_sat, green_val = cv2.cvtColor(green_average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)).astype(numpy.float64)

		# Get averaged blue HSV
		bx: int = round(n1[0] + grid_cell * (PixelCode.__SQUARE_SIZE - 11))
		by: int = round(n1[1] + grid_cell * 3.5)
		blue_region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[by - cell_size:by + cell_size, bx - cell_size:bx + cell_size, :]
		blue_average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = numpy.mean(blue_region, axis=(0, 1))
		blue_hue, blue_sat, blue_val = cv2.cvtColor(blue_average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)).astype(numpy.float64)

		# Read version data
		hue_thresh: float = 30 / 180
		sat_thresh: float = 0.3333
		val_thresh: float = 0.75
		version: int = 0

		#start = image.copy()
		#cv2.circle(start, (round(zx), round(zy)), 10, (0, 0, 0), 2)
		#cv2.imshow('Start', start)
		#cv2.waitKey()
		#return

		for i in range(math.ceil(PixelCode.__VERSION_HEADER / 2)):
			x: int = round(zx)
			y: int = round(zy - grid_cell * i)
			region: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.uint8]] = image[y - scan_size:y + scan_size, x - scan_size:x + scan_size, :]
			average: numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.float64]] = numpy.mean(region, axis=(0, 1))
			average = numpy.fmod(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_BGR2HSV).reshape((3,)), (180, 256, 256))
			h, s, v = average
			bits: int

			if (abs(h - red_hue) / 180 <= hue_thresh or abs(h - (red_hue + 180)) / 180 <= hue_thresh) and abs(s - red_sat) / 255 <= sat_thresh and abs(v - red_val) / 255 <= val_thresh:
				bits = 0b01
			elif (abs(h - green_hue) / 180 <= hue_thresh or abs(h - (green_hue + 180)) / 180 <= hue_thresh) and abs(s - green_sat) / 255 <= sat_thresh and abs(v - green_val) / 255 <= val_thresh:
				bits = 0b10
			elif (abs(h - blue_hue) / 180 <= hue_thresh or (abs(h - (blue_hue + 180)) / 180 <= hue_thresh)) and abs(s - blue_sat) / 255 <= sat_thresh and abs(v - blue_val) / 255 <= val_thresh:
				bits = 0b11
			elif s / 255 <= sat_thresh and abs(v - 255) / 255 <= val_thresh:
				bits = 0b00
			else:
				print(f'HUE: {round(h / 180 * 360)}, THRESH: {hue_thresh}')
				print(f'SAT: {round(s / 255 * 100)}, THRESH: {sat_thresh}')
				print(f'VAL: {round(v / 255 * 100)}, THRESH: {val_thresh}')
				raise CodeDecodeFailure('Failed to decode pixel-code')

			#cv2.imshow('Region', cv2.resize(region, (512, 512)))
			#cv2.imshow('Average', cv2.resize(cv2.cvtColor(average.astype(numpy.uint8).reshape((1, 1, 3)), cv2.COLOR_HSV2BGR), (512, 512)))
			#cv2.circle(image, (x, y), 3, (0xFF, 0xFF, 0x00), -1, cv2.FILLED)
			#cv2.imshow('Where', image)
			#cv2.waitKey()

			version <<= 2
			version |= bits

		# Decode binary data
		if version == 0:
			return PixelCode.__decode_version_0__(image, (red_hue, red_sat, red_val), (green_hue, green_sat, green_val), (blue_hue, blue_sat, blue_val), (hue_thresh, sat_thresh, val_thresh), (zx, zy), grid_cell, scan_size)
		elif version == 1:
			return PixelCode.__decode_version_1__(image, (red_hue, red_sat, red_val), (green_hue, green_sat, green_val), (blue_hue, blue_sat, blue_val), (hue_thresh, sat_thresh, val_thresh), (zx, zy), grid_cell, scan_size)
		else:
			raise CodeDecodeFailure(f'Invalid pixel-code version \'{version}\'')

	@staticmethod
	def try_decode(pixel_code_image: PIL.Image.Image, *, alignment_iterations: int = 4) -> typing.Optional[bytes]:
		"""
		Tries to decode binary data from a pixel-code image
		:param pixel_code_image: The pixel-code image
		:param alignment_iterations: The number of iterations to align image
		:return: The encoded binary data or None if failed
		"""

		try:
			return PixelCode.decode(pixel_code_image, alignment_iterations=alignment_iterations)
		except CodeDecodeFailure:
			return None

	def __init__(self, version: typing.Literal[0, 1]):
		"""
		Class allowing encoding and decoding for custom multicolor pixel-codes
		- Constructor -
		:param version: The pixel-code version to use
		:raises InvalidArgumentException: If 'version' is not an integer
		:raises ValueError: If 'version' is not a valid pixel-code version
		"""

		Misc.raise_ifn(isinstance(version, int), Exceptions.InvalidArgumentException(PixelCode.__init__, 'version', type(version), (int,)))
		Misc.raise_ifn(0 <= (version := int(version)) <= 1, ValueError(f'Invalid version: \'{version}\''))
		self.__version__: int = int(version)

	def encodify(self, data: bytes | bytearray, mask: PixelCode.CodeMask | int = 0b1111) -> PIL.Image.Image:
		"""
		Encodes data into a new pixel-code image
		:param data: The binary data to encode
		:param mask: The binary masks to use (defaults to all)
		:param version: The pixel-code version
		:return: The pixel-code image
		:raises ValueError: If the amount of data exceeds the maximum allowed count
		"""

		return PixelCode.encode(data, mask, version=self.__version__)

	def decodify(self, pixel_code_image: PIL.Image.Image, *, alignment_iterations: int = 4) -> bytes:
		"""
		Decodes binary data from a pixel-code image
		:param pixel_code_image: The pixel-code image
		:param alignment_iterations: The number of iterations to align image
		:return: The encoded binary data
		:raises CodeDecodeFailure: If pixel-code decode failed
		"""

		return PixelCode.decode(pixel_code_image, alignment_iterations=alignment_iterations)

	def try_decodify(self, pixel_code_image: PIL.Image.Image, *, alignment_iterations: int = 4) -> typing.Optional[bytes]:
		"""
		Tries to decode binary data from a pixel-code image
		:param pixel_code_image: The pixel-code image
		:param alignment_iterations: The number of iterations to align image
		:return: The encoded binary data or None if failed
		"""

		try:
			return PixelCode.decode(pixel_code_image, alignment_iterations=alignment_iterations)
		except CodeDecodeFailure:
			return None

	@property
	def version(self) -> int:
		"""
		:return: Gets this pixel-code transcoder's version
		"""

		return self.__version__

	@version.setter
	def version(self, version: int) -> None:
		"""
		Sets this pixel-code transcoder's version
		:param version: The new transcoder version
		:raises InvalidArgumentException: If 'version' is not an integer
		:raises ValueError: If 'version' is not a valid pixel-code version
		"""

		Misc.raise_ifn(isinstance(version, int), Exceptions.InvalidArgumentException(PixelCode.__init__, 'version', type(version), (int,)))
		Misc.raise_ifn(0 <= (version := int(version)) <= 1, ValueError(f'Invalid version: \'{version}\''))
		self.__version__: int = int(version)
