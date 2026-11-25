using System;
using Rhino.Collections;

namespace RhinoAlmondBridge
{
    public static partial class ObjectObservation
    {
        static readonly Type SharedDictionaryType = typeof(Rhino.DocObjects.Custom.UserDictionary).Assembly
            .GetType("Rhino.DocObjects.Custom.SharedUserDictionary", throwOnError: true);
        // CommonObject.UserDictionary would attach a new dictionary even on a read.
        public static ArchivableDictionary ExistingDictionary(Rhino.Runtime.CommonObject owner) =>
            (owner.UserData.Find(SharedDictionaryType) as Rhino.DocObjects.Custom.UserDictionary)?.Dictionary;
    }
}
