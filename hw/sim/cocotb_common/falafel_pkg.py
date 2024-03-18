# constants
WORD_SIZE = 8
L2_SIZE = 64
BLOCK_ALIGNMENT = L2_SIZE
# ERR_NOMEM = -1 + 2**(8*WORD_SIZE)
ERR_NOMEM = 0

OPCODE_SIZE = 4;
MSG_ID_SIZE = 8;
REG_ADDR_SIZE = 16;

# opcodes
REQ_ACCESS_REGISTER = 0
REQ_ALLOC_MEM = 1
REQ_FREE_MEM = 2

# addresses
FREE_LIST_PTR_ADDR = 0x10
LOCK_PTR_ADDR = 0x18
LOCK_ID_ADDR = 0x20


def write_config_req(req_id, addr):
    return REQ_ACCESS_REGISTER | (req_id << OPCODE_SIZE) | (addr << (OPCODE_SIZE
                                                                     + MSG_ID_SIZE))

def write_alloc_req(req_id):
    return REQ_ALLOC_MEM | (req_id << OPCODE_SIZE)

def write_free_req(req_id):
    return REQ_FREE_MEM | (req_id << OPCODE_SIZE)
