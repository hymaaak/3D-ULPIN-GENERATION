import { useQuery } from '@tanstack/react-query';
import * as parcelsApi from '../api/parcels.js';
import * as buildingsApi from '../api/buildings.js';
import * as unitsApi from '../api/units.js';
import { asList } from '../utils/constants.js';

export function useParcels(params = {}) {
  const query = useQuery({
    queryKey: ['parcels', params],
    queryFn: () => parcelsApi.listParcels({ limit: 100, ...params }),
  });
  return { ...query, parcels: asList(query.data) };
}

export function useParcel(id) {
  const query = useQuery({
    queryKey: ['parcel', id],
    queryFn: () => parcelsApi.getParcel(id),
    enabled: Boolean(id),
  });
  return { ...query, parcel: query.data };
}

export function useParcelBuildings(parcelId) {
  const query = useQuery({
    queryKey: ['parcel-buildings', parcelId],
    queryFn: () => parcelsApi.getParcelBuildings(parcelId),
    enabled: Boolean(parcelId),
  });
  return { ...query, buildings: asList(query.data) };
}

export function useBuildings(params = {}) {
  const query = useQuery({
    queryKey: ['buildings', params],
    queryFn: () => buildingsApi.listBuildings({ limit: 200, ...params }),
  });
  return { ...query, buildings: asList(query.data) };
}

export function useBuildingUnits(buildingId) {
  const query = useQuery({
    queryKey: ['building-units', buildingId],
    queryFn: () => buildingsApi.getBuildingUnits(buildingId),
    enabled: Boolean(buildingId),
  });
  return { ...query, units: asList(query.data) };
}

export function useUnits(params = {}) {
  const query = useQuery({
    queryKey: ['units', params],
    queryFn: () => unitsApi.listUnits({ limit: 200, ...params }),
  });
  return { ...query, units: asList(query.data) };
}

export function useUnitByUlpin(ulpin) {
  const query = useQuery({
    queryKey: ['unit-ulpin', ulpin],
    queryFn: () => unitsApi.getUnitByUlpin(ulpin),
    enabled: Boolean(ulpin),
    retry: false,
  });
  return { ...query, unit: query.data };
}
