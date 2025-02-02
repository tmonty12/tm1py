# -*- coding: utf-8 -*-
from typing import List

from requests import Response

from TM1py.Objects import Subset
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


class SubsetService(ObjectService):
    """ Service to handle Object Updates for TM1 Subsets (dynamic and static)
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self._process_service = ProcessService(rest)

    def create(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ create subset on the TM1 Server

            :param subset: TM1py.Subset, the subset that shall be created
            :param private: boolean

            :return:
                string: the response
        """
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}",
            subset.dimension_name,
            subset.hierarchy_name,
            subsets)
        response = self._rest.POST(url, subset.body, **kwargs)
        return response

    def get(self, subset_name: str, dimension_name: str, hierarchy_name: str = None, private: bool = False,
            **kwargs) -> Subset:
        """ get a subset from the TM1 Server

            :param subset_name: string, name of the subset
            :param dimension_name: string, name of the dimension
            :param hierarchy_name: string, name of the hierarchy
            :param private: Boolean

            :return: instance of TM1py.Subset
        """
        if not hierarchy_name:
            hierarchy_name = dimension_name
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')?$expand=Hierarchy($select=Dimension,Name),"
            "Elements($select=Name)&$select=*,Alias", dimension_name, hierarchy_name, subsets, subset_name)
        response = self._rest.GET(url=url, **kwargs)
        return Subset.from_dict(response.json())

    def get_all_names(self, dimension_name: str, hierarchy_name: str = None, private: bool = False,
                      **kwargs) -> List[str]:
        """ get names of all private or public subsets in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param private: Boolean
        :return: List of Strings
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name

        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}?$select=Name",
            dimension_name, hierarchy_name, subsets)
        response = self._rest.GET(url=url, **kwargs)
        subsets = response.json()['value']
        return [subset['Name'] for subset in subsets]

    def update(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ update a subset on the TM1 Server

        :param subset: instance of TM1py.Subset.
        :param private: Boolean
        :return: response
        """
        if subset.is_static:
            return self.update_static_subset(subset, private, **kwargs)

        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            subset.dimension_name, subset.hierarchy_name, subsets, subset.name)
        return self._rest.PATCH(url=url, data=subset.body, **kwargs)

    def make_static(self, subset_name: str, dimension_name: str, hierarchy_name: str = None,
                    private: bool = False) -> Response:
        """ convert a dynamic subset into static subset on the TM1 Server
        :param subset_name: String, name of the subset
        :param dimension_name: String, name of the dimension
        :param hierarchy_name: String, name of the hierarchy
        :param private: Boolean
        :return: response
        """
        import json
        from collections import OrderedDict
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        payload = OrderedDict()
        payload['Name'] = subset_name
        payload['MakePrivate'] = True if private else False
        payload['MakeStatic'] = True
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url("/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')/tm1.SaveAs", dimension_name,
                         hierarchy_name, subsets, subset_name)
        return self._rest.POST(url=url, data=json.dumps(payload))

    def update_or_create(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ update if exists else create

        :param subset:
        :param private:
        :return:
        """
        if self.exists(
                subset_name=subset.name,
                dimension_name=subset.dimension_name,
                hierarchy_name=subset.hierarchy_name,
                private=private,
                **kwargs):
            return self.update(subset=subset, private=private, **kwargs)

        return self.create(subset=subset, private=private, **kwargs)

    def delete(self, subset_name: str, dimension_name: str, hierarchy_name: str = None,
               private: bool = False, **kwargs) -> Response:
        """ Delete an existing subset on the TM1 Server

        :param subset_name: String, name of the subset
        :param dimension_name: String, name of the dimension
        :param hierarchy_name: String, name of the hierarchy
        :param private: Boolean
        :return:
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            dimension_name, hierarchy_name, subsets, subset_name)
        response = self._rest.DELETE(url=url, **kwargs)
        return response

    def exists(self, subset_name: str, dimension_name: str, hierarchy_name: str = None, private: bool = False,
               **kwargs) -> bool:
        """checks if private or public subset exists

        :param subset_name: 
        :param dimension_name: 
        :param hierarchy_name:
        :param private:
        :return: boolean
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        subset_type = 'PrivateSubsets' if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            dimension_name, hierarchy_name, subset_type, subset_name)
        return self._exists(url, **kwargs)

    def delete_elements_from_static_subset(self, elements: list[str], dimension_name: str, hierarchy_name: str, subset_name: str,
                                           private: bool = False, **kwargs) -> Response:
        if not hierarchy_name: hierarchy_name = dimension_name
        subsets = "PrivateSubsets" if private else "Subsets"
        for element_name in elements:
            url = format_url(
                "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')/Elements('{}')",
                dimension_name, hierarchy_name, subsets, subset_name, element_name)
            
            response = self._rest.DELETE(url=url, **kwargs)
            if response.status_code != 204: return response
        return response
        

    def get_element_names(self, dimension_name: str, hierarchy_name: str, subset_name: str, private: bool = False,
                          **kwargs) -> List[str]:
        """ Get elements from existing (dynamic or static) subset

        :param dimension_name:
        :param hierarchy_name:
        :param subset_name:
        :param private:
        :param kwargs:
        :return:
        """
        subset = self.get(subset_name, dimension_name, hierarchy_name, private=private, **kwargs)
        if subset.is_static:
            return subset.elements

        mdx = subset.expression
        from TM1py import ElementService
        element_service = ElementService(self._rest)
        tuples = element_service.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name"],
            element_properties=None,
            parent_properties=None,
            **kwargs)
        return [entry[0]["Name"] for entry in tuples]

    def update_static_subset(self, subset, private, **kwargs) -> Subset:
        original_subset = self.get(subset_name=subset.name, dimension_name=subset.dimension_name, 
                                    hierarchy_name=subset.hierarchy_name, private=private, **kwargs)
    
        for element in subset.elements:
            if element in original_subset.elements:
                subset.elements.remove(element)
        
        elements_to_be_deleted = []
        for element in original_subset.elements:
            if element not in subset.elements:
                elements_to_be_deleted.append(element)

        response = self.delete_elements_from_static_subset(elements_to_be_deleted, dimension_name=subset.dimension_name, 
                                                hierarchy_name=subset.hierarchy_name, subset_name=subset.name, private=private)
        if response.status_code != 204: return response
        
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            subset.dimension_name, subset.hierarchy_name, subsets, subset.name)
        return self._rest.PATCH(url=url, data=subset.body, **kwargs)
        


