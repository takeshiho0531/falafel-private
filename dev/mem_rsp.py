from cocotb.triggers import FallingEdge, RisingEdge

from free_list import LinkedList


async def send_req_to_allocate(dut, clk):
    await FallingEdge(clk)
    dut.is_alloc_i.setimmediatevalue(1)
    dut.req_alloc_valid_i.setimmediatevalue(1)
    dut.size_to_allocate_i.setimmediatevalue(200)
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.req_alloc_valid_i.setimmediatevalue(0)


async def send_req_to_free(dut, clk, addr_to_free):
    await FallingEdge(clk)
    dut.is_alloc_i.setimmediatevalue(0)
    dut.req_alloc_valid_i.setimmediatevalue(1)
    dut.addr_to_free_i.setimmediatevalue(addr_to_free)
    await FallingEdge(clk)
    await RisingEdge(clk)
    dut.req_alloc_valid_i.setimmediatevalue(0)


async def grant_store(dut, clk):
    dut.mem_req_rdy_i.setimmediatevalue(0)
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(0)
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)
    dut.mem_req_rdy_i.setimmediatevalue(1)


async def send_rsp_from_mem(
    dut, clk, addr, linked_list: LinkedList, data, expected_next_addr=None
):
    if (addr - 8) in linked_list.nodes:
        # store updated only next_addr
        linked_list.update_next_addr(addr - 8, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
    elif (addr) in linked_list.nodes:
        # store updated size
        linked_list.update_size(addr, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
        assert dut.mem_req_data_o == expected_next_addr, int(dut.mem_req_data_o)  # noqa
        linked_list.update_next_addr(addr, int(dut.mem_req_data_o))
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await grant_store(dut, clk)
    else:  # store updated size
        linked_list.add_node(addr, data)
        await FallingEdge(clk)
        await grant_store(dut, clk)
        assert dut.mem_req_data_o == expected_next_addr, int(dut.mem_req_data_o)  # noqa
        linked_list.update_next_addr(addr, int(dut.mem_req_data_o))
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await grant_store(dut, clk)

    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(1)
    await FallingEdge(clk)


async def send_load_rsp_from_mem(dut, clk, addr, linked_list: LinkedList):
    if (dut.mem_req_addr_o.value.integer - 8) in linked_list.nodes:
        await send_next_addr_from_mem(dut, clk, addr, linked_list)
    else:
        await FallingEdge(clk)
        await send_size_from_mem(dut, clk, addr, linked_list)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await FallingEdge(clk)
        await send_next_addr_from_mem(dut, clk, addr, linked_list)

    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(1)
    await FallingEdge(clk)


async def send_size_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[0])
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)


async def send_next_addr_from_mem(dut, clk, addr, linked_list: LinkedList):
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(linked_list.get_node(addr)[1])
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)


async def grant_lock(dut, clk):
    await FallingEdge(clk)
    await RisingEdge(clk)
    await FallingEdge(clk)
    dut.mem_req_rdy_i.setimmediatevalue(0)
    dut.mem_rsp_val_i.setimmediatevalue(1)
    dut.mem_rsp_data_i.setimmediatevalue(0)
    await FallingEdge(clk)
    dut.mem_rsp_val_i.setimmediatevalue(0)
    dut.mem_req_rdy_i.setimmediatevalue(1)
