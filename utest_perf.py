#!/bin/env python3
import unittest
import bandwidth_tester

class PerfTests(unittest.TestCase):
    import bandwidth_tester
    bandwidth_tester.quietPlaybooks = True

    #test tool itself
    def test_regions(self):
        listRegions = bandwidth_tester.list_regions()
        self.assertIn('us-east-2', listRegions, 'the is no us-east-2. Broken function? Broken API? Broken amazon?')
        self.assertIn(member='us-east-2', container=listRegions, msg='the is no us-east-2. Broken function? Broken API? Broken amazon?')

    #same as above
    def test_images(self):
        self.assertRegex(bandwidth_tester.image('us-east-2'),r'^ami-[a-z0-9]+')

    #same as above
    def test_networks(self):
        self.assertRegex(bandwidth_tester.list_subnets('us-east-2')[0], r'^subnet-[a-z0-9]+')

    #test speed of standard configurations of containers
    @unittest.skip
    def test_instances(self):
        self.assertGreater(bandwidth_tester.instancetest(region='us-east-2',instance_type_client='t2.micro',instance_type_server='t2.micro'),50000000,'something wrong with speed!')

    #test speed of custom vCPUs
    @unittest.skip
    def test_cpu(self):
        self.assertGreater(bandwidth_tester.instancetest(region='us-east-2',instance_type_client='m5.large', instance_type_server='m5.large', vcpu_client=1, vcpu_server=1), 800000000,'something wrong with speed!')

    #test standard deviation
    def test_standard_deviation(self):
        results = []
        for i in range(10):
            results.append(bandwidth_tester.instancetest(region='us-east-2', instance_type_client='t3.micro',instance_type_server='t2.micro'))

        average_speed = sum(results)/len(results)
        mse = sum([ (speed - average_speed)**2 for speed in results])
        print(f"mse={mse}")
        self.assertLess(mse,1500)


if __name__ == '__main__':
    unittest.main()

