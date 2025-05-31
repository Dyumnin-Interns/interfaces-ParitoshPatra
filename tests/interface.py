import cocotb
from cocotb.triggers import RisingEdge, Timer,Event, ClockCycles
from cocotb_bus.drivers import BusDriver
import random




class WriteInterface(BusDriver):
	_signals = ["CLK", "RST_N", "write_address","write_data","write_rdy","write_en","read_address","read_en","read_rdy","read_data"]
	
	def __init__(self,dut,name,clk):
		super().__init__(dut,name,clk)
		self.bus.write_en.value = 0
		self.clk = clk

	async def _driver_send(self, value, sync=True):
		for i in range(random.randint(0,20)):
			await RisingEdge(self.clk)
		if(self.bus.write_rdy.value.integer != 1):
			await RisingEdge(self.bus.write_rdy)
		self.bus.write_en.value = 1
		self.bus.write_address.value = value.get('addr')
		self.bus.write_data.value = value.get('val')
		await RisingEdge(self.clk)
		self.bus.write_en.value = 0



class ReadInterface(BusDriver):
    _signals = ["CLK", "RST_N", "write_address", "write_data", "write_rdy",
                "write_en", "read_address", "read_en", "read_rdy", "read_data"]

    def __init__(self, dut, name, clk):
        super().__init__(dut, name, clk)
        self.bus.read_en.value = 0
        self.clk = clk

    async def _driver_send(self, value, sync=True):
        await RisingEdge(self.clk)
        if (self.bus.read_rdy.value.integer != 1):
            await RisingEdge(self.bus.read_rdy)
        self.bus.read_en.value = 1
        self.bus.read_address.value = value.get('addr')
        await RisingEdge(self.clk)
        self.bus.read_en.value = 0
