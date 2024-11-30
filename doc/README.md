# Falafel v2 document <!-- omit in toc -->
last update: Nov 24, 2024

- [terms](#terms)
- [falafel\_core](#falafel_core)
  - [states](#states)
- [falafel\_lsu](#falafel_lsu)
  - [states](#states-1)
- [interfaces \& interactions between core, lsu and mem](#interfaces--interactions-between-core-lsu-and-mem)


## terms
- [header](#header): <br>
Falafel v2 uses a linked list structure for managing its free list; the block size of the free block<br>
The header contains the metadata located at the beginning of each free block; the size of the free block & the address of the next header address <br>
![header image](img/header.png)
- header_data: <br>
the data in the header (block size & next address) + the address of the header
- [insert / delete header](#insert_delete)
![insert delete header image](img/insert_delete.png)
## falafel_core
the part responsible for the first-fit or the best-fit algorithm

### states
※　a request to the lsu occurs in the `REQ_*` states <br>
※　falafel_core can only receive a response from lsu in the `WAIT_RSP_FROM_LSU` state.

- `IDLE`
- `REQ_ACQUIRE_LOCK`: 
    request lock; <br>
    if the allocator acquire the lock, then it can move to starting the process of its memory allocating
- `REQ_RELEASE_LOCK`:
    release lock after the process of memory allocating
- `REQ_LOAD_HEADER`: cf. [header](#header)
- `CMP_SIZE`
- `REQ_INSERT_NEW_HEADER`: cf. [insert / delete header](#insert_delete)
- `REQ_DELETE_HEADER`: cf. [insert / delete header](#insert_delete)
- `WAIT_RSP_FROM_LSU`

## falafel_lsu
the part responsible for interactions with memory

### states
※　a request to the mem occurs in the `REQ_*` states <br>
※　falafel_lsu can only receive a response from lsu in the `WAIT_RSP_FROM_MEM` state.



- `IDLE`
- `LOAD_KEY`: <br>
    request loading the key to the mem (to check whether the lock is open or not at the point)
- `LOCK_DO_CAS`:
    request the lock 
- `UNLOCK_KEY`: request unlocking
- `LOAD_SIZE`: <br>
    request loading the size of the free block to the mem
- `LOAD_NEXT_ADDR`: <br>
    request loading the next header address of the free block to the mem
- `STORE_UPDATED_SIZE`: <br>
    request storing the size of the free block to the mem (setting the updated size of the free block)
- `STORE_UPDATED_NEXT_ADDR`
    request storing the next header address of the free block to the mem (setting te updated next address of the free block)
- `WAIT_RSP_FROM_MEM`
- `SEND_RSP_TO_CORE`

## interfaces & interactions between core, lsu and mem
- the interface overview
![interface overview](img/interface_overview.png)
- the interactions in each procedure
    - lock: <br>
    ![interaction lock](img/interaction_lock.png)
    - load header: <br>
    ![interaction load header](img/interaction_load_header.png)
    - update header: cf. [insert / delete header](#insert_delete) <br>
    ![interaction update header](img/interaction_insert.png)
    - delete header: cf. [insert / delete header](#insert_delete) <br>
    ![interaction delete header](img/interaction_delete.png)
    - release lock: <br>
    ![interaction release lock](img/interaction_release_lock.png)