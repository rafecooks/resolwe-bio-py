"""Relation resource."""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from resdk.exceptions import ValidationError

from .base import BaseResource
from .utils import get_collection_id, get_sample_id, is_collection


class Relation(BaseResource):
    """Resolwe Relation resource.

    One and only one of the identifiers (slug, id or model_data)
    should be given.

    :param slug: Resource slug
    :type slug: str
    :param id: Resource ID
    :type id: int
    :param model_data: Resource model data
    :type model_data: dict
    :param resolwe: Resolwe instance
    :type resolwe: Resolwe object

    """

    endpoint = 'relation'

    WRITABLE_FIELDS = ('collection', 'label') + BaseResource.WRITABLE_FIELDS
    UPDATE_PROTECTED_FIELDS = ('entities', 'type') + BaseResource.UPDATE_PROTECTED_FIELDS

    def __init__(self, slug=None, id=None,  # pylint: disable=redefined-builtin
                 model_data=None, resolwe=None):
        """Initialize attributes."""
        #: collection id in which relation is
        self._collection = None
        #: (lazy loaded) collection object in which relation is
        self._hydrated_collection = None
        #: (lazy loaded) list of samples in the relation
        self._samples = None

        #: list of entities in the relation
        self.entities = []
        #: type of the relation
        self.type = None
        #: optional label of the relation
        self.label = None

        super(Relation, self).__init__(slug, id, model_data, resolwe)

        #: list of the sample positions in the relation or `None` in none of the positions is set
        self.positions = [
            entity_obj['position'] if 'position' in entity_obj else None
            for entity_obj in self.entities
        ]
        if not any(self.positions):
            self.positions = None

        self.logger = logging.getLogger(__name__)

    @property
    def samples(self):
        """Return list of the sample objects in the relation."""
        if not self._samples:
            sample_ids = [entity_obj['entity'] for entity_obj in self.entities]
            self._samples = self.resolwe.sample.filter(id__in=','.join(map(str, sample_ids)))
            # Samples should be sorted, so they have same order as positions
            self._samples = sorted(self._samples, key=lambda sample: sample_ids.index(sample.id))
        return self._samples

    @property
    def collection(self):
        """Return collection object to which relation belongs."""
        if not self._hydrated_collection:
            self._hydrated_collection = self.resolwe.collection.get(self._collection)
        return self._hydrated_collection

    @collection.setter
    def collection(self, collection):
        """Set collection to which relation belongs."""
        self._collection = get_collection_id(collection)
        # Save collection if already hydrated, othervise it will be rerived in getter
        self._hydrated_collection = collection if is_collection(collection) else None

    def update(self):
        """Clear cache and update resource fields from the server."""
        self._samples = None
        self._hydrated_collection = None

        super(Relation, self).update()

    def add_sample(self, sample, position=None):
        """Add ``sample`` object to the collection."""
        payload = [{
            'entity': get_sample_id(sample),
            'position': position
        }]
        self.api(self.id).add_entity.post(payload)
        self.update()

    def remove_samples(self, *samples):
        """Remove ``sample`` objects from the collection."""
        samples = [get_sample_id(sample) for sample in samples]
        self.api(self.id).remove_entity.post({'ids': samples})
        self.update()

    def save(self):
        """Check that collection is saved and save instance."""
        if self._collection is None:
            # `save` fails in an ugly way if collection is not set
            raise ValidationError('`collection` attribute is required.')

        super(Relation, self).save()

    def __repr__(self):
        """Format relation name."""
        if self.positions:
            pairs = [
                '{}: {}'.format(position, sample.name)
                for position, sample in zip(self.positions, self.samples)
            ]
            samples = '{{{}}}'.format(', '.join(pairs))
        else:
            samples = '[{}]'.format(', '.join(sample.name for sample in self.samples))

        label = ""
        if self.label:
            label = "label: '{}', ".format(self.label)

        return "{} <id:{} type: '{}', {}samples: {}>".format(
            self.__class__.__name__, self.id, self.type, label, samples
        )
