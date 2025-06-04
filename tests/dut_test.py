import logging
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer,Event, ClockCycles
from interface import ReadInterface, WriteInterface
from cocotb.log import SimLog
from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver

import random 
import constraint



@CoverPoint("top.a",
		xf = lambda x,y:x,
		bins=[0,1]
		)


@CoverPoint("top.b",
                xf = lambda x,y:y,
                bins=[0,1]
                )


@CoverCross("top.cross.ab",
            items=['top.a','top.b'])



def sample(x,y):
    pass 




@CoverPoint("top.w.wd_addr",
            xf = lambda wd_addr,wd_en, wd_data, rd_en, rd_addr: wd_addr,
            bins=[4,5])

@CoverPoint("top.w.wd_data",
            xf = lambda wd_addr,wd_en, wd_data, rd_en, rd_addr: wd_data,
            bins=[0,1])

@CoverPoint("top.w.wd_en",
            xf = lambda wd_addr,wd_en, wd_data, rd_en, rd_addr: wd_en,
            bins=[0,1])

@CoverPoint("top.r.rd_addr",
            xf = lambda wd_addr,wd_en, wd_data, rd_en, rd_addr: rd_addr,
            bins=[0,1,2,3])

@CoverPoint("top.r.rd_en",
            xf = lambda wd_addr,wd_en, wd_data, rd_en, rd_addr: rd_en,
            bins=[0,1])

@CoverCross("top.cross.w",
            items=['top.w.wd_addr', 'top.w.wd_data', 'top.w.wd_en'] 
            )

@CoverCross("top.cross.r",
            items=["top.r.rd_en", "top.r.rd_addr"])

def fl_cv(wd_addr, wd_en, wd_data, rd_en, rd_addr):
    pass


class TestBench:
    def __init__(self, name, entity):
        self.name = name
        self.entity = entity
        self.CLK = Clock
        self.a_ls = []
        self.b_ls = []
        self.y_ls = []
        self.stats = []
        self.writer_event = Event()
        self.reader_event = Event()
        self.ref_address = {'A_status': 0, 'B_status': 1, 'Y_status': 2, 
                            'Y_output': 3, 'A_data': 4, 'B_data': 5
                           }
        self.writer = WriteInterface(entity, "", entity.CLK)
        self.reader = ReadInterface(entity, "", entity.CLK)

    async def reset_dut(self):
        await RisingEdge(self.entity.CLK)

        self.entity.write_address.value = 0
        self.entity.write_data.value = 0
        self.entity.write_en.value = 0
        self.entity.read_en.value = 0
        self.entity.read_data.value = 0
        self.entity.read_address.value = 0

        self.entity.RST_N.value = 1
        await ClockCycles(self.entity.CLK, 4)
        self.entity.RST_N.value = 0
        await ClockCycles(self.entity.CLK, 4)
        self.entity.RST_N.value = 1
        await RisingEdge(self.entity.CLK)

        print("\t\t reset done")


    
    def stat_dec(self, addr, val):
        if addr == 3:
            self.stats.append({'name': 'y_out', 'val': val})
        elif addr == 4:
            self.stats.append({'name': 'a_write', 'val': val})
        elif addr == 5:
            self.stats.append({'name': 'b_write', 'val': val})
        elif addr == 0:
            self.stats.append({'name': 'a_status', 'val': f"{'full' if val == 0 else 'empty'}"})
        elif addr == 1:
            self.stats.append({'name': 'b_status', 'val': f"{'full' if val == 0 else 'empty'}"})
        elif addr == 2:
            self.stats.append({'name': 'y_status', 'val': f"{'full' if val == 1 else 'empty'}"})
    
    def cvr(self):
        self.p = constraint.Problem()
        self.p.addVariable('write_en', [0,1])
        self.p.addVariable('read_en', [0,1])
        self.p.addVariable('write_address', [4,5])
        self.p.addVariable('read_address', [0,1,2,3])
        self.p.addVariable('write_data', [0,1])
        self.p.addVariable('write_rdy', [1])
        self.p.addVariable('read_rdy', [1])

        self.p.addConstraint(lambda r_en, w_en, r_rdy: r_en == 1 
                             if w_en == 0 and r_rdy == 1 
                             else r_en == 0, ['read_en', 'write_en', 'read_rdy'])
        self.p.addConstraint(lambda r_en, w_en, w_rdy: w_en == 1 
                             if r_en == 0 and w_rdy == 1 
                             else w_en == 0, ['read_en', 'write_en', 'write_rdy'])

    def solve(self):
        self.cvr()
        self.sols = self.p.getSolutions()

    def get_sols(self):
        return random.choice(self.sols)




@cocotb.test()
async def dut_test(dut):
    cocotb.start_soon(Clock(dut.CLK, 2, "ns").start())

    log = SimLog("interface_test")
    logging.getLogger().setLevel(logging.INFO)
    
    tbh = TestBench(name="tb inst", entity=dut)
    await tbh.reset_dut()


    test_vectors = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for a, b in test_vectors:
        await tbh.writer._driver_send({'addr': 4, 'val': a})
        await tbh.writer._driver_send({'addr': 5, 'val': b})
        sample(a, b)
        await tbh.reader._driver_send({'addr': 3})
        print(f"[Functional] A={a}, B={b}, Y={dut.read_data.value.integer}")

    tbh.solve()
    for i in range(40):
        x = tbh.get_sols()
        fl_cv(x.get("write_address"), x.get("write_en"), x.get("write_data"), x.get("read_en"), x.get("read_address"))

        if x.get("read_en") == 1:
            await tbh.reader._driver_send({'addr': x.get('read_address')})
            print(f"[{i}] Read addr {x.get('read_address')} -> {dut.read_data.value.integer}")
            tbh.stat_dec(x.get('read_address'), dut.read_data.value.integer)

		fl_cv(None,0,None,1,x.get('read_address'))


        elif x.get("write_en") == 1:
            await tbh.writer._driver_send({'addr': x.get('write_address'), 'val': x.get('write_data')})
            print(f"[{i}] Write addr {x.get('write_address')} <- {x.get('write_data')}")
            tbh.stat_dec(x.get('write_address'), x.get('write_data'))

		fl_cv(x.get('write_address'),1,x.get('write_data'),0,None)


        await RisingEdge(dut.CLK)

    for entry in tbh.stats:
        print(f"Stat: {entry}")

    coverage_db.report_coverage(print, bins=True)
    print(f"Functional Coverage (A×B): {coverage_db['top.cross.ab'].cover_percentage:.2f}%")
    print(f"Write Coverage: {coverage_db['top.cross.w'].cover_percentage:.2f}%")
    print(f"Read Coverage: {coverage_db['top.cross.r'].cover_percentage:.2f}%")






