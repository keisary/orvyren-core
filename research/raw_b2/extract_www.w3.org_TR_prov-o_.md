# https://www.w3.org/TR/prov-o/

# PROV-O: The PROV Ontology
URL: https://www.w3.org/TR/prov-o/

PROV-O: The PROV Ontology

## W3C Recommendation 30 April 2013

This version:
: http://www.w3.org/TR/2013/REC-prov-o-20130430/
Latest published version:
: http://www.w3.org/TR/prov-o/
Implementation report:
: http://www.w3.org/TR/2013/NOTE-prov-implementations-20130430/
Previous version:
: http://www.w3.org/TR/2013/PR-prov-o-20130312/
Editors:
: Timothy Lebo, Rensselaer Polytechnic Institute, USA
: Satya Sahoo, Case Western Reserve University, USA
: Deborah McGuinness, Rensselaer Polytechnic Institute, USA
Contributors:
: (In alphabetical order)
: Khalid Belhajjame, University of Manchester, UK
: James Cheney, University of Edinburgh, UK
: David Corsar, University of Aberdeen, UK
: Daniel Garijo, Ontology Engineering Group, Universidad PolitÃ©cnica de Madrid, Spain
: Stian Soiland-Reyes, University of Manchester, UK
: Stephan Zednik, Rensselaer Polytechnic Institute, USA
: Jun Zhao, University of Oxford, UK

 Please refer to the errata for this document, which may include some normative corrections. 

The English version of this specification is the only normative version. Non-normative translations may also be available.

## Abstract

The PROV Ontology (PROV-O) expresses the PROV Data Model [PROV-DM] using the OWL2 Web Ontology Language (OWL2) [OWL2-OVERVIEW]. It provides a set of classes, properties, and restrictions that can be used to represent and interchange provenance information generated in different systems and under different contexts. It can also be specialized to create new classes and properties to model provenance information for different applications and domains. The PROV Document Overview describes the overall state of PROV, and should be read before other PROV documents. 

The namespace for all PROV-O terms is http://www.w3.org/ns/prov#. 

The OWL encoding of the PROV Ontology is available here. 

## Status of This Document

 This section describes the status of this document at the time of its publication. Other documents may supersede this document. A list of current W3C publications and the latest revision of this technical report can be found in the W3C technical reports index at http://www.w3.org/TR/. 

#### PROV Family of Documents

 This document is part of the PROV family of documents, a set of documents defining various aspects that are necessary to achieve the vision of inter-operable interchange of provenance information in heterogeneous environments such as the Web. These documents are listed below. Please consult the [PROV-OVERVIEW] for a guide to reading these documents. 

- PROV-OVERVIEW (Note), an overview of the PROV family of documents [PROV-OVERVIEW];
- PROV-PRIMER (Note), a primer for the PROV data model [PROV-PRIMER];
- PROV-O (Recommendation), the PROV ontology, an OWL2 ontology allowing the mapping of the PROV data model to RDF (this document);
- PROV-DM (Recommendation), the PROV data model for provenance [PROV-DM];
- PROV-N (Recommendation), a notation for provenance aimed at human consumption [PROV-N];