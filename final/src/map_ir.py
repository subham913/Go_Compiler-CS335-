from asm_utils import *

opcode = {
	'int+' : 'addl',
	'int-' : 'subl',
	'int*' : 'imul',
	'int/' : 'idiv',
	'int%' : 'idiv'
}

jumps = {
	'<' : 'jg',
	'>' : 'jl',
	'<=' : 'jge',
	'>=' : 'jle',
	'==' : 'je',
	'!=' : 'jne'
}

def get_opcode(x):
	if x in opcode.keys():
		return opcode[x]
	else:
		return None

def get_jump(x):
	if x in jumps.keys():
		return jumps[x]
	else:
		return None
	
def separate(var):
	name = var.split('(')[0]
	scope = var.split('(')[1].split(')')[0]
	return name, int(scope)

def type_size(t):		
	if t == 'int':
		return 4
	elif t == 'float':
		return 8
	elif t[0:6] == 'Struct':
		res = 0
		field_dic = ast.literal_eval(t[6:])
		for variables in field_dic:
			res += type_size(field_dic[variables])
		return res
	elif t[0:5] == 'Array':
		return 4
		try:
			length = int(t[6:-1].split(',')[0])
			element_type = ','.join(t[6:-1].split(',')[1:])[1:]
			return length*type_size(element_type)
		except:
			print 'currently not supported'
			# length = t[6:-1].split(',')[0]
			# element_type = ','.join(t[6:-1].split(',')[1:])[1:]
			return 4
	return 1

def get_offset(var, scope_list):
	name, scope = separate(var)
	table = scope_list[scope].table
	offset = table[name]['offset']
	if offset >= 0:
		return str(-(offset + 4))
	else:
		return str(-offset)

def is_immediate(var):
	if '(' in var and ')' in var:
		return False
	else:
		return True

def map_instr(instr, scope_list, fp):
	# print instr.instr, instr.type
	if type(instr.type) == tuple and instr.type[0] == 'if':
		jump = get_jump(instr.type[1])
		
		if is_immediate(instr.src1) and is_immediate(instr.src2):
			gen_instr('movl $' + str(instr.src2) + ', %edx', fp)
			gen_instr('cmp $' + str(instr.src1) + ', %edx', fp)
		elif is_immediate(instr.src1):
			src2_offset = get_offset(instr.src2, scope_list)
			gen_instr('movl ' + str(src2_offset) + '(%ebp), %edx', fp)
			gen_instr('cmp $' + str(instr.src1) + ', %edx', fp)
		elif is_immediate(instr.src2):
			src1_offset = get_offset(instr.src1, scope_list)
			gen_instr('movl ' + str(src1_offset) + '(%ebp), %ecx', fp)
			gen_instr('movl $' + str(instr.src2) + ', %edx', fp)
			gen_instr('cmp %ecx, %edx', fp)
		else:
			src1_offset = get_offset(instr.src1, scope_list)
			src2_offset = get_offset(instr.src2, scope_list)
			gen_instr('movl ' + str(src1_offset) + '(%ebp), %ecx', fp)
			gen_instr('movl ' + str(src2_offset) + '(%ebp), %edx', fp)
			gen_instr('cmp %ecx, %edx', fp)
		
		gen_instr(jump + ' ' +  instr.dest, fp)
		
	elif type(instr.type) == tuple and instr.type[0] == 'binop':
		arg = instr.type[1]
		if arg[-1] == 'i': # one of the two is an immediate operand
			opcode = get_opcode(arg[:-1])
			if not opcode:
				print 'operation not supported'
			elif opcode == 'idiv':
				if is_immediate(instr.src1): # dest := imm / src2 OR dest := imm % src2
					src2_offset = get_offset(instr.src2, scope_list)
					dest_offset = get_offset(instr.dest, scope_list)
					gen_instr('movl $' + instr.src1 + ', %eax', fp)
					gen_instr('cdq', fp)
					gen_instr('movl ' + str(src2_offset) + '(%ebp), %ebx', fp)
					gen_instr('idiv %ebx', fp)
					if arg[-2] == '/':
						gen_instr('movl %eax, ' + str(dest_offset) + '(%ebp)', fp)
					if arg[-2] == '%':
						gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)
				
				elif is_immediate(instr.src2): # dest := src1 / imm OR dest := src1 % imm
					src1_offset = get_offset(instr.src1, scope_list)
					dest_offset = get_offset(instr.dest, scope_list)
					gen_instr('movl ' + str(src1_offset) + '(%ebp), %eax', fp)
					gen_instr('cdq', fp)
					gen_instr('movl $' + instr.src2 + ', %ebx', fp)
					gen_instr('idiv %ebx', fp)
					if arg[-2] == '/':
						gen_instr('movl %eax, ' + str(dest_offset) + '(%ebp)', fp)
					if arg[-2] == '%':
						gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)
			else:
				if is_immediate(instr.src1): # dest := imm op src2
					src2_offset = get_offset(instr.src2, scope_list)
					dest_offset = get_offset(instr.dest, scope_list)
					gen_instr('movl $' + instr.src1 + ', %edx', fp)
					gen_instr('movl ' + str(src2_offset) + '(%ebp), %ecx', fp)
					gen_instr(opcode + ' %ecx, %edx', fp)
					gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)	
				
				elif is_immediate(instr.src2): # dest := src1 op imm
					src1_offset = get_offset(instr.src1, scope_list)
					dest_offset = get_offset(instr.dest, scope_list)
					gen_instr('movl ' + str(src1_offset) + '(%ebp), %edx', fp)
					gen_instr(opcode + ' $' + str(instr.src2) + ', %edx', fp)
					gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)
		
		else: # src1 and src2 are variables - temporary or otherwise
			opcode = get_opcode(arg)
			if not opcode:
				print 'operation not supported'
			elif opcode == 'idiv':
				src1_offset = get_offset(instr.src1, scope_list)
				src2_offset = get_offset(instr.src2, scope_list)
				dest_offset = get_offset(instr.dest, scope_list)
				gen_instr('movl ' + str(src1_offset) + '(%ebp), %eax', fp)
				gen_instr('cdq', fp)
				gen_instr('movl ' + str(src2_offset) + '(%ebp), %ebx', fp)
				gen_instr('idiv %ebx', fp)
				if arg[-1] == '/':
					gen_instr('movl %eax, ' + str(dest_offset) + '(%ebp)', fp)
				if arg[-1] == '%':
					gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)
			else:
				src1_offset = get_offset(instr.src1, scope_list)
				src2_offset = get_offset(instr.src2, scope_list)
				dest_offset = get_offset(instr.dest, scope_list)
				gen_instr('movl ' + str(src1_offset) + '(%ebp), %ecx', fp)
				gen_instr('movl ' + str(src2_offset) + '(%ebp), %edx', fp)
				if opcode == 'subl':
					gen_instr(opcode + ' %edx, %ecx', fp)
					gen_instr('movl %ecx, ' + str(dest_offset) + '(%ebp)', fp)
				else:
					gen_instr(opcode + ' %ecx, %edx', fp)
					gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)

	elif instr.type == 'assign':
		dest_offset = get_offset(instr.dest, scope_list) # returns correctly even if [] present 
		if '[' in instr.dest:
			index = (instr.dest).split('[')[1].split(']')[0]
			elem_size = int((instr.dest).split('[')[1].split(']')[1])
			if is_immediate(index):
				array_offset = int(index) * elem_size
				# print var, index, elem_size, array_offset
				# address of array's first element
				gen_instr('movl ' + dest_offset + '(%ebp), %edx', fp)
				if is_immediate(instr.src1):
					gen_instr('movl $' + str(instr.src1) + ', ' + str(array_offset) + '(%edx)', fp)
				else:
					src_offset = get_offset(instr.src1, scope_list)
					gen_instr('movl ' + str(src_offset) + '(%ebp), %ecx', fp)
					gen_instr('movl %ecx, ' + str(array_offset) + '(%edx)', fp)
			else:
				index_offset = get_offset(index, scope_list)
				gen_instr('movl ' + str(index_offset) + '(%ebp), %ebx', fp)
				gen_instr('imul $' + str(elem_size) + ', %ebx', fp) 
				gen_instr('addl ' + dest_offset + '(%ebp), %ebx', fp) # now ebx contains address of the element which contain a[i]	
				if is_immediate(instr.src1):
					gen_instr('movl $' + instr.src1 + ', (%ebx)', fp)
				else:
					src_offset = get_offset(instr.src1, scope_list)
					gen_instr('movl ' + str(src_offset) + '(%ebp), %ecx', fp)
					gen_instr('movl %ecx, (%ebx)', fp)
				
		elif '[' in instr.src1:
			src_offset = get_offset(instr.src1, scope_list) # returns correctly even if [] present 
			index = (instr.src1).split('[')[1].split(']')[0]
			elem_size = int((instr.src1).split('[')[1].split(']')[1])
			if is_immediate(index):
				array_offset = int(index) * elem_size
				# print index, elem_size, array_offset
				# address of array's first element
				gen_instr('movl ' + src_offset + '(%ebp), %edx', fp)
				dest_offset = get_offset(instr.dest, scope_list)
				gen_instr('movl ' + str(array_offset) + '(%edx), %ecx', fp)
				gen_instr('movl %ecx, ' + str(dest_offset) + '(%ebp)', fp)
			else:
				index_offset = get_offset(index, scope_list)
				# print 'here', index_offset
				gen_instr('movl ' + str(index_offset) + '(%ebp), %ebx', fp)
				gen_instr('imul $' + str(elem_size) + ', %ebx', fp) 
				gen_instr('addl ' + src_offset + '(%ebp), %ebx', fp)

				dest_offset = get_offset(instr.dest, scope_list)
				gen_instr('movl (%ebx), %ecx', fp)
				gen_instr('movl %ecx, ' + str(dest_offset) + '(%ebp)', fp)
		
		# a[2] = a[1] should never be in 3ac because a[1] is always assigned tempvar	
		elif '[' in instr.src1 and '[' in instr.dest:
			print 'error: wrong ircode'
		else:
			if is_immediate(instr.src1):
				gen_instr('movl $' + str(instr.src1) + ', ' + str(dest_offset) + '(%ebp)', fp)
			else:
				src_offset = get_offset(instr.src1, scope_list)
				gen_instr('movl ' + str(src_offset) + '(%ebp), %edx', fp)
				gen_instr('movl %edx, ' + str(dest_offset) + '(%ebp)', fp)

	elif instr.type == 'allocate':
		dest_offset = get_offset(instr.dest, scope_list)

		# allocate space in stack
		if instr.src1 == 'NULL':
			None
		else:
			if is_immediate(instr.src1):
				space = int(instr.src1) * type_size(instr.src2)
				gen_instr('subl $' + str(space) + ', %esp', fp)
				# set starting address of array to be the current esp value
				gen_instr('movl %esp, ' + dest_offset + '(%ebp)', fp)

	elif instr.type == 'goto':
		gen_instr('jmp ' + instr.dest, fp)

	elif instr.type == 'print':
		if instr.dest == 'int':
			if is_immediate(instr.src1):
				gen_instr('movl $' + instr.src1 + ', %edx', fp)
				gen_instr('pushl %edx', fp)
			else:
				src1_offset = get_offset(instr.src1, scope_list)
				gen_instr('pushl ' + str(src1_offset) + '(%ebp)', fp)
			gen_instr('pushl $outFormatInt', fp)
			gen_instr('call printf', fp)
			gen_instr('pop %ebx', fp)
			gen_instr('pop %ebx', fp)
		else:
			print 'unsupported types for print'

	elif instr.type == 'callvoid':
		gen_instr('call ' + instr.dest, fp)
		gen_instr('addl $' + instr.src1 + ', %esp', fp) # pop values from stack

	elif instr.type == 'callint':
		gen_instr('call ' + instr.src1, fp)
		dest_offset = get_offset(instr.dest, scope_list)
		gen_instr('movl -12(%esp), %edx', fp)
		gen_instr('movl %edx, ' + dest_offset + '(%ebp)', fp)
		gen_instr('addl $' + '4' + ', %esp', fp) #TODO

	elif instr.type == 'parameter':
		if is_immediate(instr.dest):
			gen_instr('pushl $' + instr.dest, fp)
		else:
			dest_offset = get_offset(instr.dest, scope_list)
			gen_instr('pushl ' + dest_offset + '(%ebp)', fp)

	elif instr.type == 'retval':
		if is_immediate(instr.src1):
			gen_instr('movl $' + instr.src1 + ', %edx', fp)
		else:
			src_offset = get_offset(instr.src1, scope_list)
			gen_instr('movl ' + src_offset + '(%ebp), %edx', fp)
		gen_instr('movl %edx, -4(%ebp)', fp)

	elif instr.type == 'label':
		if not instr.dest:
			gen_label(instr.instr.split(':')[0], fp)
		else: # function call case
			if instr.dest == 'main':
				gen_label('__main__', fp)
			else:
				gen_label(instr.dest, fp)
			
			gen_instr('pushl %ebp', fp)
			gen_instr('movl %esp, %ebp', fp)
			table = scope_list[0].table
			scope = scope_list[table[instr.dest]['func_dict']['symbol_table']]
			gen_instr('subl $' + str(scope.offset) + ', %esp', fp)
	
	elif instr.type == 'retvoid':
		gen_instr("movl %ebp, %esp", fp)
  		gen_instr("pop %ebp", fp)
		gen_instr("ret", fp)

