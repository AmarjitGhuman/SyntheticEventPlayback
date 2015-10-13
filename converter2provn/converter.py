"""
Copyright 2015 Palo Alto Research Center, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Coded by rui@parc.com
"""
import json
from pprint import pprint
import sys
import optparse
import datetime

class FD2PN(object):
    """FiveDirections Simulator Data to TC's ADAPT PROV-N"""

    setAgents = {}
    setEntities = {}
    tmpPID = {}

    def iso8601(self, t):
        delta = datetime.timedelta(seconds=t)
        epoch = datetime.datetime.strptime("1970-01-01", "%Y-%m-%d")
        time_str = str((epoch + delta).isoformat()) + 'Z'
        return time_str

    def pretty_print_agent(self):
        ret = []
        for key in self.setAgents:
            value = self.setAgents[key]
            ret.append('agent(ex:ag{}, [prov:type=\'adapt:unitOfExecution\',' . format(value['index']))
            ret.append('\tadapt:machineID = \'{}\',' . format(value['adapt:machineID']))
            if "foaf:accountName" in value:
                ret.append('\tfoaf:name = \'{}\',' . format(value['foaf:name']))
                ret.append('\tfoaf:accountName = \'{}\'])\n' . format(value['foaf:accountName']))
            else:
                ret.append('\tfoaf:name = \'{}\'])\n' . format(value['foaf:name']))
        return ret

    def pretty_print_entities(self):
        ret = []
        for key in self.setEntities:
            value = self.setEntities[key]
            ret.append('entity(ex:ent{}, [\
                  \n\tprov:type=adapt:artifact,\
                  \n\tadapt:artifactType=\'{}\',\
                  \n\tadapt:filePath=\'{}\'])\n' . format(value['index'], value['type'],
                                                        value['dir'] + value['file']))
        return ret

    def getAgents(self,value):
        agent = value['host'] + '_' + str(value['pid'])
        if(agent not in self.setAgents):
            agProperties = {}
            agProperties['adapt:machineID'] = value['host']
            agProperties['foaf:name'] = value['process']
            if 'user' in value:
                agProperties['foaf:accountName'] = value['user']
            agProperties['index'] = value['index']
            self.setAgents[agent] = agProperties

    def getEntities(self, key, value):
        if('file' not in value):
            value['file'] = "\\"
        entity = value['dir'] + "\\" + value['file']
        if(entity not in self.setEntities):
            eProperties = {}
            eProperties['dir'] = value['dir']
            eProperties['file'] = value['file']
            eProperties['index'] = value['index']
            eProperties['type'] = key
            self.setEntities[entity] = eProperties

    def encodeProcess(self,value):
        ret = []
        ret.append('activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID=\'{}\',\
        \n\tfoaf:accountName=\'{}\',\
        \n\tadapt:pwd=\'{}\',\
        \n\tprov:atTime=\'{}\',\
        \n\tadapt:pid=\'{}\',\
        \n\tadapt:ppid=\'{}\',\
        \n\tadapt:privs=\'{}\',\
        \n\tadapt:cmdLine=\'{}\',\
        \n\tadapt:cmdString=\'{}\'])\n' . format(value['index'], value['host'], value['user'], value['dir'],
                                               self.iso8601(value['time']), value['pid'], value['ppid'],
                                               value['elevation'], value['cmd'], value['cmd']))

        kk = str(value['ppid']) + "_" + value['file']
        activity = self.tmpPID[kk] if kk in self.tmpPID else 0
        ret.append('wasStartedBy(ex:act{}, ex:act{}, {}, [\
            \n\tprov:atTime=\'{}\'])\n' . format(value['index'], activity,
                                                      self.iso8601(value['time']), self.iso8601(value['time'])))
        return ret

    def encodeFile(self, value):
        ret = []
        ret.append('activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID=\'{}\',\
        \n\tprov:atTime=\'{}\',\
        \n\tadapt:pid=\'{}\',\
        \n\tadapt:cmdLine=\'{}\',\
        \n\tadapt:cmdString=\'{}\'])\n' . format(value['index'], value['host'],
                                               self.iso8601(value['time']), value['pid'],
                                               value['process'], value['process']))

        ret.append('wasAssociatedWith(ex:as{}, ex:act{}, ex:ag{}, -, -)\n' . format(value['index'],
                                                                value['index'], value['index']))

        ret.append('used(ex:us{}, ex:act{}, ex:ent{}, \'{}\', [adapt:useOp=\'{}\'])\n' . format(value['index'],
                                                            value['index'], value['index'],
                                                            self.iso8601(value['time']), value['action']))

        kk = str(value['pid']) + "_" + value['file']
        self.tmpPID[kk] = "ex:act" + str(value['index'])
        return ret

    def encodeNetwork(self, value):
        ret = []
        ret.append('entity(ex:socket{}, [prov:type=adapt:artifact])\n' . format(value['index']))

        ret.append('dc:description(ex:socket{}, [\
            \n\tprov:type=adapt:metadata,\
            \n\tadapt:dstPortID=\'{}\',\
            \n\tadapt:srcPort=\'{}\',\
            \n\tadapt:srcIP=\'{}\',\
            \n\tadapt:dstIP=\'{}\',\
            \n\tadapt:host=\'{}\',\
            \n\tadapt:protocol=\'{}\'])\n' . format(value['index'],
                                         value['dport'],
                                         value['sport'],
                                         value['saddr'],
                                         value['daddr'],
                                         value ['host'],
                                         value['protocol']))

        ret.append('wasAssociatedWith(ex:as{}, ex:a{}, ex:ag{}, -, [])\n' . format(value['index'], value['index'], value['index']))
        ret.append('wasGeneratedBy(ex:e{}, ex:a{}, -, [adapt:genOp=\'{}\', prov:atTime=\'{}\'])\n' . format(value['index'], value['index'],
                                                                                    value['action'], self.iso8601(value['time'])))
        return ret

    def encodeRegistry(self, value):
        ret = []
        ret.append('entity(ex:reg{}, [\
        \n\tprov:type=adapt:artifact,\
        \n\tadapt:artifactType=\'registryEntry\',\
        \n\tadapt:registryKey=\'{}\'])\n' . format(value['index'],value['key']))

        ret.append('activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID=\'{}\',\
        \n\tprov:atTime=\'{}\',\
        \n\tadapt:pid=\'{}\',\
        \n\tadapt:cmdLine=\'{}\',\
        \n\tadapt:cmdString=\'{}\'])\n' . format(value['index'], value['host'],
                                               self.iso8601(value['time']), value['pid'],
                                               value['process'], value['process']))

        ret.append('wasGeneratedBy(ex:wgb{}, ex:reg{}, ex:ent{}, -, [\
        \n\tadapt:genOp=\'{}\',\
        \n\tadapt:registryValue=\'{}\',\
        \n\tadapt:registryType=\'{}\'])\n' . format(value['index'], value['index'], value['index'],
                                                  value['action'], value['newval'], value['newtype']))

        return ret

    def encodeExit(self, value):
        ret = []

        ret.append('activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID=\'{}\',\
        \n\tprov:atTime=\'{}\',\
        \n\tadapt:pid=\'{}\',\
        \n\tadapt:cmdLine=\'{}\',\
        \n\tadapt:cmdString=\'{}\'])\n' . format(value['index'], value['host'],
                                               self.iso8601(value['time']), value['pid'],
                                               value['process'], value['process']))


        ret.append('wasAssociatedWith(ex:as{}, ex:act{}, ex:ag{}, -, [\
        \n\tadapt:genOp=\'ret_val\',\
        \n\tadapt:returnVal=\'{}\'])\n' . format(value['index'], value['index'], value['index'], value['code']))

        return ret

    def json2Prov(self, json):
        pp = ["document\n", "prefix ex <http://example.org/>", "prefix adapt <http://adapt.galois.com/>",
              "prefix foaf <http://xmlns.com/foaf/0.1/>", "prefix dc <http://purl.org/dc/elements/1.1/>",
              "prefix nfo <http://www.semanticdesktop.org/ontologies/2007/03/22/nfo/v1.2/>", ""]

        for i in xrange(len(decoded)):
            for key, value in decoded[i].items() :
                if(key=='file' or key=='network' or key=='registry' or key=='exit'):
                    self.getAgents(value)
                if(key=='file'):
                    self.getEntities(key, value)

        pp += self.pretty_print_agent()
        pp += self.pretty_print_entities()

        for i in xrange(len(decoded)):
            for key, value in decoded[i].items():
                if(key=='file'):
                    pp += self.encodeFile(value)
                elif(key=='process'):
                    pp += self.encodeProcess(value)
                elif(key=='registry'):
                    pp += self.encodeRegistry(value)
                elif(key=='network'):
                    pp += self.encodeNetwork(value)
                elif(key=='exit'):
                    pp += self.encodeExit(value)
                else:
                    print >>sys.stderr, "Parsing error (ignoring entry): " + key

        pp.append("end document")
        return pp

#with open('youtube.txt') as data_file:
#    data = json.load(data_file)
if __name__ == '__main__':
    usage = "usage: %prog inputFile outputFile"
    optp = optparse.OptionParser(usage = usage, version = "%prog 1.0")

    opts, args = optp.parse_args()
    optp.parse_args()

    if not (len(args) == 2):
        optp.error("Missing file argument")

    with open(args[0]) as f:
        content = f.readlines()

    outFile =  open(args[1], "w")
    fs2pn = FD2PN()
    for i in xrange(1,len(content)):
        if(i % 9 == 0):
            print >>sys.stderr, "Decoding line " + str(i)
            decoded = json.loads(content[i-1])
            #print json.dumps(decoded, sort_keys=True, indent=4)
            lst = fs2pn.json2Prov(decoded)
            outFile.write('\n'.join(lst))
