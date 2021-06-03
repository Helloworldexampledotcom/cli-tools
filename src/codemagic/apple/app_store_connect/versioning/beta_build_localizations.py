from dataclasses import dataclass
from typing import Generator
from typing import Optional
from typing import Type
from typing import Union

from codemagic.apple.app_store_connect.resource_manager import ResourceManager
from codemagic.apple.resources import Build
from codemagic.apple.resources import ResourceId
from codemagic.apple.resources import ResourceType
from codemagic.apple.resources.beta_build_localization import BetaBuildLocalization


class BetaBuildLocalizations(ResourceManager[BetaBuildLocalization]):
    """
    Beta Build Localizations
    https://developer.apple.com/documentation/appstoreconnectapi/prerelease_versions_and_beta_testers/beta_build_localizations
    """

    @property
    def resource_type(self) -> Type[BetaBuildLocalization]:
        return BetaBuildLocalization

    @dataclass
    class Filter(ResourceManager.Filter):
        build: Optional[ResourceId] = None
        locale: Optional[str] = None

    def create(self, build: Union[ResourceId, Build], locale: str, whats_new: str) -> BetaBuildLocalization:
        """
        https://developer.apple.com/documentation/appstoreconnectapi/create_a_beta_build_localization
        """
        attributes = {
            'locale': locale,
            'whatsNew': whats_new,
        }

        relationships = {
            'build': {
                'data': self._get_attribute_data(build, ResourceType.BUILDS),
            },
        }

        payload = self._get_create_payload(
            ResourceType.BETA_BUILD_LOCALIZATIONS, attributes=attributes, relationships=relationships)
        response = self.client.session.post(f'{self.client.API_URL}/betaBuildLocalizations', json=payload).json()
        return BetaBuildLocalization(response['data'], created=True)

    def modify(self, build: Union[ResourceId, Build], locale: str, whats_new: str) -> BetaBuildLocalization:
        """
        https://developer.apple.com/documentation/appstoreconnectapi/modify_a_beta_build_localization
        """
        resource_id = self._get_resource_id(build)
        localization = next(self.list(self.Filter(build=resource_id, locale=locale)))

        payload = self._get_update_payload(
            localization.id, ResourceType.BETA_BUILD_LOCALIZATIONS, attributes={'whatsNew': whats_new})

        response = self.client.session.patch(
            f'{self.client.API_URL}/betaBuildLocalizations/{localization.id}', json=payload).json()
        return BetaBuildLocalization(response['data'])

    def list(self, resource_filter: Filter = Filter()) -> Generator[BetaBuildLocalization, None, None]:
        """
        https://developer.apple.com/documentation/appstoreconnectapi/list_beta_app_localizations
        """
        beta_build_localizations = self.client.paginate(
            f'{self.client.API_URL}/betaBuildLocalizations', params=resource_filter.as_query_params())
        return (BetaBuildLocalization(localization) for localization in beta_build_localizations)

    def delete(self, build: Union[ResourceId, Build], locale):
        """
        https://developer.apple.com/documentation/appstoreconnectapi/delete_a_beta_build_localization
        """
        resource_id = self._get_resource_id(build)
        localization = next(self.list(self.Filter(build=resource_id, locale=locale)))
        self.client.session.delete(f'{self.client.API_URL}/betaBuildLocalizations/{localization.id}')
